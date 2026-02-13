#!/usr/bin/env python3
"""Pi-side control server for hexapod web controller.

- Serves a local controller website.
- Receives control commands via HTTP POST.
- Runs a fixed-rate control loop that can be hooked to real robot code.

No third-party dependencies required.
"""

from __future__ import annotations

import json
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


def clamp(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


class HexapodController:
    """Hook this class into your servo/gait code."""

    def __init__(self) -> None:
        self._last_print = 0.0

    def apply(self, state: ControlState) -> None:
        # Replace this block with real calls into your movement stack.
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
                body = json.dumps(state).encode("utf-8")
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
            if self.path != "/api/control":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._set_json(400)
                self.wfile.write(b'{"ok":false,"error":"invalid_json"}')
                return

            sanitized = {
                "mode": str(payload.get("mode", "stop")),
                "vx": clamp(payload.get("vx"), -1.0, 1.0, 0.0),
                "vy": clamp(payload.get("vy"), -1.0, 1.0, 0.0),
                "turn": clamp(payload.get("turn"), -1.0, 1.0, 0.0),
                "speed": clamp(payload.get("speed"), 0.0, 1.0, 0.4),
                "height": clamp(payload.get("height"), -1.0, 1.0, 0.0),
            }
            state = asdict(shared.update(sanitized))
            body = json.dumps({"ok": True, "state": state}).encode("utf-8")
            self._set_bytes(200, "application/json", len(body))
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
    shared = SharedState()
    controller = HexapodController()

    thread = threading.Thread(target=control_loop, args=(shared, controller), daemon=True)
    thread.start()

    server = ThreadingHTTPServer((HOST, PORT), build_handler(shared))
    print(f"Web controller available at http://<pi-ip>:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
