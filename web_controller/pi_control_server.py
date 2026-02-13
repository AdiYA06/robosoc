#!/usr/bin/env python3
"""Pi-side control server for hexapod web controller.

- Serves a local controller website.
- Receives control commands via HTTP POST.
- Runs a fixed-rate control loop that can be hooked to real robot code.

No third-party dependencies required.
"""

from __future__ import annotations

import argparse
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

    def __init__(self, transport: "LineTransport") -> None:
        self.transport = transport
        self._last_print = 0.0

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
        if now - self._last_print >= 0.15:
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
        self._connect()

    def _connect(self) -> None:
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
        except Exception as exc:
            if self.required:
                raise RuntimeError(f"Failed to open serial port {self.port}") from exc
            print(f"Serial transport not available on {self.port}: {exc}")
            self._serial = None

    def send_line(self, text: str) -> None:
        if self._serial is None:
            return
        try:
            self._serial.write((text + "\n").encode("utf-8"))
        except Exception:
            self._serial = None
            if self.required:
                raise

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass


def build_handler(shared: SharedState):
    class Handler(BaseHTTPRequestHandler):
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
            if self.path == "/api/state":
                state = asdict(shared.get())
                body = json.dumps({"state": state, "lock": shared.lock_status()}).encode("utf-8")
                self._set_bytes(200, "application/json", len(body))
                self.wfile.write(body)
                return

            rel_path = "index.html" if self.path == "/" else self.path.lstrip("/")
            file_path = (STATIC_DIR / rel_path).resolve()

            if not str(file_path).startswith(str(STATIC_DIR)) or not file_path.exists():
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
    args = parser.parse_args()

    shared = SharedState()
    if args.serial_port:
        transport: LineTransport = SerialTransport(args.serial_port, args.baud, args.serial_required)
    else:
        print("Serial forwarding disabled (no --serial-port).")
        transport = StdoutTransport()

    controller = HexapodController(transport)

    thread = threading.Thread(target=control_loop, args=(shared, controller), daemon=True)
    thread.start()

    server = ThreadingHTTPServer((args.host, args.port), build_handler(shared))
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