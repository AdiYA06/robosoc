#!/usr/bin/env python3
"""Pi-side control server for hexapod web controller.

- Serves a local controller website.
- Receives control commands via HTTP POST.
- Runs a fixed-rate control loop that can be hooked to real robot code.

No third-party dependencies required.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = "0.0.0.0"
PORT = 8080
CONTROL_HZ = 25.0
COMMAND_TIMEOUT_S = 0.7
LOCK_TIMEOUT_S = 2.0
STATIC_DIR = Path(__file__).resolve().parent / "static"
SHARED_UI_DIR = Path(__file__).resolve().parents[1] / "shared_ui"


@dataclass
class ControlState:
    mode: str = "stop"  # stop, walk, turn, stance
    vx: float = 0.0      # -1..1
    vy: float = 0.0      # -1..1
    turn: float = 0.0    # -1..1
    speed: float = 0.4   # 0..1
    height: float = 0.0  # -1..1
    updated_at: float = 0.0


class SharedState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = ControlState(updated_at=time.time())
        self._owner_id = ""
        self._owner_seen_at = 0.0

    def update(self, patch: dict[str, Any]) -> ControlState:
        with self._lock:
            for key, value in patch.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
            self._state.updated_at = time.time()
            return ControlState(**asdict(self._state))

    def get(self) -> ControlState:
        with self._lock:
            return ControlState(**asdict(self._state))

    def lock_status(self) -> dict[str, Any]:
        with self._lock:
            active = bool(self._owner_id) and (time.time() - self._owner_seen_at) <= LOCK_TIMEOUT_S
            return {
                "active": active,
                "owner_id": self._owner_id if active else "",
                "timeout_s": LOCK_TIMEOUT_S,
            }

    def update_from_client(self, client_id: str, patch: dict[str, Any]) -> tuple[bool, ControlState, dict[str, Any]]:
        now = time.time()
        with self._lock:
            lease_expired = (now - self._owner_seen_at) > LOCK_TIMEOUT_S
            if not self._owner_id or lease_expired:
                self._owner_id = client_id
                self._owner_seen_at = now
            elif client_id != self._owner_id:
                status = {
                    "active": True,
                    "owner_id": self._owner_id,
                    "timeout_s": LOCK_TIMEOUT_S,
                }
                return False, ControlState(**asdict(self._state)), status
            else:
                self._owner_seen_at = now

            for key, value in patch.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
            self._state.updated_at = now
            status = {
                "active": True,
                "owner_id": self._owner_id,
                "timeout_s": LOCK_TIMEOUT_S,
            }
            return True, ControlState(**asdict(self._state)), status

    def force_takeover(self, client_id: str) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            self._owner_id = client_id
            self._owner_seen_at = now
            return {
                "ok": True,
                "lock": {
                    "active": True,
                    "owner_id": self._owner_id,
                    "timeout_s": LOCK_TIMEOUT_S,
                },
            }


def clamp(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


class HexapodController:
    """Hook this class into your servo/gait code."""

    def __init__(self, transport: "LineTransport", verbose_stream: bool = False, event_logs: bool = True) -> None:
        self.transport = transport
        self.verbose_stream = verbose_stream
        self.event_logs = event_logs
        self._last_print = 0.0
        self._last_mode: str | None = None
        self._last_moving = False

    def apply(self, state: ControlState) -> None:
        packet = {
            "mode": state.mode,
            "vx": state.vx,
            "vy": state.vy,
            "turn": state.turn,
            "speed": state.speed,
            "height": state.height,
            "ts": time.time(),
        }
        self.transport.send_line(json.dumps(packet))

        now = time.time()
        moving = abs(state.vx) > 0.02 or abs(state.vy) > 0.02 or abs(state.turn) > 0.02
        mode_changed = state.mode != self._last_mode
        movement_changed = moving != self._last_moving

        if self.verbose_stream and (now - self._last_print >= 0.15):
            self._last_print = now
            print(
                "mode={mode:>6} vx={vx:+.2f} vy={vy:+.2f} turn={turn:+.2f} "
                "speed={speed:.2f} height={height:+.2f}".format(
                    mode=state.mode,
                    vx=state.vx,
                    vy=state.vy,
                    turn=state.turn,
                    speed=state.speed,
                    height=state.height,
                )
            )
        elif self.event_logs and (mode_changed or movement_changed):
            print(f"control mode={state.mode} moving={'yes' if moving else 'no'} speed={state.speed:.2f}")

        self._last_mode = state.mode
        self._last_moving = moving


class LineTransport:
    def send_line(self, text: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return


class StdoutTransport(LineTransport):
    def send_line(self, text: str) -> None:
        return


class SerialTransport(LineTransport):
    def __init__(self, port: str, baudrate: int, required: bool) -> None:
        self.port = port
        self.baudrate = baudrate
        self.required = required
        self._serial = None
        self._last_connect_attempt = 0.0
        self._connect_retry_s = 0.8
        self._last_connect_error = ""
        self._connect()

    def _connect(self) -> None:
        self._last_connect_attempt = time.time()
        try:
            import serial  # type: ignore
        except Exception as exc:
            if self.required:
                raise RuntimeError("pyserial is required for serial transport") from exc
            print("Serial disabled: install pyserial to enable USB forwarding.")
            return

        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=0.01)
            print(f"Serial transport connected: {self.port} @ {self.baudrate}")
            self._last_connect_error = ""
        except Exception as exc:
            if self.required:
                msg = str(exc)
                if msg != self._last_connect_error:
                    print(f"Serial transport unavailable on {self.port}: {exc}")
                    self._last_connect_error = msg
            else:
                print(f"Serial transport not available on {self.port}: {exc}")
            self._serial = None

    def send_line(self, text: str) -> None:
        now = time.time()
        if self._serial is None:
            if (now - self._last_connect_attempt) >= self._connect_retry_s:
                self._connect()
            if self._serial is None:
                return

        if self._serial is None:
            return
        try:
            self._serial.write((text + "\n").encode("utf-8"))
        except Exception:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
            print("Serial write failed; will retry connection.")

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass


def build_handler(shared: SharedState, auth_user: str | None, auth_pass: str | None):
    class Handler(BaseHTTPRequestHandler):
        def _is_authorized(self) -> bool:
            if auth_user is None or auth_pass is None:
                return True
            header = self.headers.get("Authorization", "")
            if not header.startswith("Basic "):
                return False
            encoded = header.split(" ", 1)[1].strip()
            try:
                decoded = base64.b64decode(encoded).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                return False
            user, sep, password = decoded.partition(":")
            if not sep:
                return False
            return hmac.compare_digest(user, auth_user) and hmac.compare_digest(password, auth_pass)

        def _request_auth(self) -> None:
            body = b"Authentication required"
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("WWW-Authenticate", 'Basic realm="Hexapod Controller"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _set_json(self, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _set_bytes(self, status: int, content_type: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self) -> None:
            if not self._is_authorized():
                self._request_auth()
                return

            if self.path == "/api/state":
                state = asdict(shared.get())
                body = json.dumps({"state": state, "lock": shared.lock_status()}).encode("utf-8")
                self._set_bytes(200, "application/json", len(body))
                self.wfile.write(body)
                return

            if self.path == "/":
                file_path = (SHARED_UI_DIR / "index.html").resolve()
            elif self.path == "/styles.css":
                file_path = (SHARED_UI_DIR / "styles.css").resolve()
            else:
                rel_path = self.path.lstrip("/")
                file_path = (STATIC_DIR / rel_path).resolve()

            in_static = str(file_path).startswith(str(STATIC_DIR))
            in_shared = str(file_path).startswith(str(SHARED_UI_DIR))
            if (not in_static and not in_shared) or not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            content = file_path.read_bytes()
            if file_path.suffix == ".html":
                ctype = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            else:
                ctype = "application/octet-stream"
            self._set_bytes(200, ctype, len(content))
            self.wfile.write(content)

        def do_POST(self) -> None:
            if not self._is_authorized():
                self._request_auth()
                return

            if self.path not in {"/api/control", "/api/takeover"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._set_json(400)
                self.wfile.write(b'{"ok":false,"error":"invalid_json"}')
                return
            client_id = str(payload.get("client_id", "")).strip()
            if not client_id:
                self._set_json(400)
                self.wfile.write(b'{"ok":false,"error":"missing_client_id"}')
                return

            if self.path == "/api/takeover":
                body = json.dumps(shared.force_takeover(client_id)).encode("utf-8")
                self._set_bytes(200, "application/json", len(body))
                self.wfile.write(body)
                return

            sanitized = {
                "mode": str(payload.get("mode", "stop")),
                "vx": clamp(payload.get("vx"), -1.0, 1.0, 0.0),
                "vy": clamp(payload.get("vy"), -1.0, 1.0, 0.0),
                "turn": clamp(payload.get("turn"), -1.0, 1.0, 0.0),
                "speed": clamp(payload.get("speed"), 0.0, 1.0, 0.4),
                "height": clamp(payload.get("height"), -1.0, 1.0, 0.0),
            }
            ok, state_obj, lock = shared.update_from_client(client_id, sanitized)
            state = asdict(state_obj)
            status_code = 200 if ok else 409
            body = json.dumps({"ok": ok, "state": state, "lock": lock}).encode("utf-8")
            self._set_bytes(status_code, "application/json", len(body))
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def control_loop(shared: SharedState, controller: HexapodController) -> None:
    dt = 1.0 / CONTROL_HZ
    while True:
        state = shared.get()
        stale = (time.time() - state.updated_at) > COMMAND_TIMEOUT_S
        if stale:
            state.mode = "stop"
            state.vx = 0.0
            state.vy = 0.0
            state.turn = 0.0
        controller.apply(state)
        time.sleep(dt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hexapod web controller + serial forwarder")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--serial-port", default=os.getenv("SERIAL_PORT", ""))
    parser.add_argument("--baud", type=int, default=int(os.getenv("SERIAL_BAUD", "115200")))
    parser.add_argument("--serial-required", action="store_true")
    parser.add_argument("--verbose-stream", action="store_true", help="Print continuous state stream")
    parser.add_argument("--internet", action="store_true", help="Enable internet-ready mode (requires auth)")
    parser.add_argument("--auth-user", default=os.getenv("HEXAPOD_AUTH_USER", ""))
    parser.add_argument("--auth-pass", default=os.getenv("HEXAPOD_AUTH_PASS", ""))
    args = parser.parse_args()

    auth_user: str | None = None
    auth_pass: str | None = None
    auth_requested = args.internet or args.auth_user or args.auth_pass
    if auth_requested:
        if not args.auth_user or not args.auth_pass:
            parser.error("--internet requires both --auth-user and --auth-pass (or HEXAPOD_AUTH_USER / HEXAPOD_AUTH_PASS)")
        auth_user = args.auth_user
        auth_pass = args.auth_pass

    shared = SharedState()
    if args.serial_port:
        transport: LineTransport = SerialTransport(args.serial_port, args.baud, args.serial_required)
    else:
        print("Serial forwarding disabled (no --serial-port).")
        transport = StdoutTransport()

    controller = HexapodController(transport, verbose_stream=args.verbose_stream)

    thread = threading.Thread(target=control_loop, args=(shared, controller), daemon=True)
    thread.start()

    server = ThreadingHTTPServer((args.host, args.port), build_handler(shared, auth_user, auth_pass))
    if auth_user is None:
        print("Auth: disabled (LAN only).")
    else:
        print("Auth: enabled (HTTP Basic).")
    print(f"Web controller available at http://<pi-ip>:{args.port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        server.server_close()


if __name__ == "__main__":
    main()
