#!/usr/bin/env python3
"""Internet relay server for hexapod control.

- Hosts the remote controller UI.
- Accepts authenticated control commands.
- Enforces single-controller lock with lease timeout.
- Exposes a polling endpoint for the Raspberry Pi bridge.

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import secrets
import threading
import time
from dataclasses import dataclass, asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass
class ControlState:
    mode: str = "stop"
    vx: float = 0.0
    vy: float = 0.0
    turn: float = 0.0
    speed: float = 0.4
    height: float = 0.0
    ts: float = 0.0


class RelayState:
    def __init__(self, auth_token: str, lease_seconds: int) -> None:
        self.auth_token = auth_token
        self.lease_seconds = lease_seconds
        self.lock = threading.Lock()
        self.session_id = ""
        self.owner = ""
        self.lease_until = 0.0
        self.seq = 0
        self.command = ControlState(ts=time.time())

    def _lease_active(self) -> bool:
        return bool(self.session_id) and time.time() < self.lease_until

    def _touch(self) -> None:
        self.lease_until = time.time() + self.lease_seconds

    def login(self, token: str, owner: str) -> dict[str, Any]:
        with self.lock:
            if token != self.auth_token:
                return {"ok": False, "error": "unauthorized"}
            sid = secrets.token_urlsafe(24)
            return {"ok": True, "session": sid, "owner": owner or "operator"}

    def claim(self, session: str, owner: str) -> dict[str, Any]:
        with self.lock:
            if not session:
                return {"ok": False, "error": "missing_session"}
            if self._lease_active() and session != self.session_id:
                return {
                    "ok": False,
                    "error": "busy",
                    "owner": self.owner,
                    "lease_until": self.lease_until,
                }

            self.session_id = session
            self.owner = owner or "operator"
            self._touch()
            return {
                "ok": True,
                "owner": self.owner,
                "lease_until": self.lease_until,
            }

    def renew(self, session: str) -> dict[str, Any]:
        with self.lock:
            if not self._lease_active() or session != self.session_id:
                return {"ok": False, "error": "not_owner"}
            self._touch()
            return {"ok": True, "lease_until": self.lease_until}

    def submit(self, session: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            if not self._lease_active() or session != self.session_id:
                return {"ok": False, "error": "not_owner"}

            self._touch()
            self.seq += 1
            self.command = ControlState(
                mode=str(payload.get("mode", "stop")),
                vx=clamp(payload.get("vx"), -1.0, 1.0, 0.0),
                vy=clamp(payload.get("vy"), -1.0, 1.0, 0.0),
                turn=clamp(payload.get("turn"), -1.0, 1.0, 0.0),
                speed=clamp(payload.get("speed"), 0.0, 1.0, 0.4),
                height=clamp(payload.get("height"), -1.0, 1.0, 0.0),
                ts=time.time(),
            )
            return {
                "ok": True,
                "seq": self.seq,
                "command": asdict(self.command),
                "lease_until": self.lease_until,
            }

    def snapshot(self, since_seq: int) -> dict[str, Any]:
        with self.lock:
            lease_active = self._lease_active()
            if not lease_active:
                safe_cmd = ControlState(mode="stop", speed=self.command.speed, height=self.command.height, ts=time.time())
                return {
                    "ok": True,
                    "changed": since_seq < self.seq,
                    "seq": self.seq,
                    "command": asdict(safe_cmd),
                    "owner": "",
                    "lease_active": False,
                    "lease_until": 0.0,
                }
            return {
                "ok": True,
                "changed": since_seq < self.seq,
                "seq": self.seq,
                "command": asdict(self.command),
                "owner": self.owner,
                "lease_active": True,
                "lease_until": self.lease_until,
            }


def clamp(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(value)
    except Exception:
        return default
    return max(lo, min(hi, x))


def build_handler(state: RelayState):
    class Handler(BaseHTTPRequestHandler):
        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                return None

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/poll":
                qs = parse_qs(parsed.query)
                since = int(qs.get("since", ["0"])[0])
                self._write_json(200, state.snapshot(since))
                return

            rel_path = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
            file_path = (STATIC_DIR / rel_path).resolve()
            if not str(file_path).startswith(str(STATIC_DIR)) or not file_path.exists() or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            content = file_path.read_bytes()
            ctype = "application/octet-stream"
            if file_path.suffix == ".html":
                ctype = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:
            payload = self._read_json()
            if payload is None:
                self._write_json(400, {"ok": False, "error": "invalid_json"})
                return

            if self.path == "/api/login":
                out = state.login(str(payload.get("token", "")), str(payload.get("owner", "")))
                self._write_json(200 if out.get("ok") else 401, out)
                return

            if self.path == "/api/claim":
                out = state.claim(str(payload.get("session", "")), str(payload.get("owner", "")))
                self._write_json(200 if out.get("ok") else 409, out)
                return

            if self.path == "/api/renew":
                out = state.renew(str(payload.get("session", "")))
                self._write_json(200 if out.get("ok") else 403, out)
                return

            if self.path == "/api/command":
                out = state.submit(str(payload.get("session", "")), payload)
                self._write_json(200 if out.get("ok") else 403, out)
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Hexapod internet relay")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--token", required=True, help="shared operator token")
    parser.add_argument("--lease-seconds", type=int, default=10)
    args = parser.parse_args()

    state = RelayState(auth_token=args.token, lease_seconds=args.lease_seconds)
    server = ThreadingHTTPServer((args.host, args.port), build_handler(state))

    print(f"Relay listening on http://{args.host}:{args.port}")
    print("Use HTTPS + reverse proxy in production.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
