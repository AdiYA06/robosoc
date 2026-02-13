#!/usr/bin/env python3
"""Pi bridge: pulls commands from internet relay and forwards to Servo 2040 serial."""

from __future__ import annotations

import argparse
import json
import time
from urllib.request import urlopen


def poll(relay_base: str, since: int) -> dict:
    with urlopen(f"{relay_base}/api/poll?since={since}", timeout=2.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Hexapod relay bridge")
    parser.add_argument("--relay", required=True, help="relay base URL, e.g. https://robot.example.com")
    parser.add_argument("--serial-port", required=True, help="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--hz", type=float, default=25.0)
    args = parser.parse_args()

    import serial  # type: ignore

    ser = serial.Serial(args.serial_port, args.baud, timeout=0.02)
    dt = 1.0 / max(1.0, args.hz)
    seq = 0

    print(f"Bridge connected serial: {args.serial_port} @ {args.baud}")
    print(f"Polling relay: {args.relay}")

    safe_cmd = {"mode": "stop", "vx": 0.0, "vy": 0.0, "turn": 0.0, "speed": 0.4, "height": 0.0, "ts": 0.0}

    try:
        while True:
            t0 = time.time()
            try:
                payload = poll(args.relay.rstrip("/"), seq)
                seq = int(payload.get("seq", seq))
                cmd = payload.get("command", safe_cmd)
            except Exception:
                cmd = safe_cmd

            ser.write((json.dumps(cmd) + "\n").encode("utf-8"))
            elapsed = time.time() - t0
            if elapsed < dt:
                time.sleep(dt - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
