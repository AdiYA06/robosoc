#!/usr/bin/env python3
"""Pi-side polling client for university-hosted hexapod commands.

Reads command JSON from a remote PHP endpoint and forwards to serial transport.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from math import atan2, degrees

from pi_control_server import ControlState, HexapodController, LineTransport, SerialTransport, StdoutTransport

DEFAULT_POLL_HZ = 20.0
DEFAULT_STALE_TIMEOUT_S = 1.5


def clamp(value: object, lo: float, hi: float, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


def fetch_state(endpoint: str, api_token: str, timeout_s: float) -> tuple[bool, ControlState | None, float, float]:
    req = urllib.request.Request(
        endpoint,
        method='GET',
        headers={
            'X-API-Token': api_token,
            'Accept': 'application/json',
        },
    )
    request_start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        request_rtt_s = time.monotonic() - request_start
        return False, None, 0.0, request_rtt_s

    if not isinstance(payload, dict) or payload.get('ok') is not True:
        request_rtt_s = time.monotonic() - request_start
        return False, None, 0.0, request_rtt_s

    state_data = payload.get('state')
    if not isinstance(state_data, dict):
        request_rtt_s = time.monotonic() - request_start
        return False, None, 0.0, request_rtt_s

    mode = str(state_data.get('mode', 'stop'))
    if mode not in {'stop', 'walk', 'turn', 'stance'}:
        mode = 'stop'

    state = ControlState(
        mode=mode,
        vx=clamp(state_data.get('vx'), -1.0, 1.0, 0.0),
        vy=clamp(state_data.get('vy'), -1.0, 1.0, 0.0),
        turn=clamp(state_data.get('turn'), -1.0, 1.0, 0.0),
        speed=clamp(state_data.get('speed'), 0.0, 1.0, 0.4),
        height=clamp(state_data.get('height'), -1.0, 1.0, 0.0),
        updated_at=time.time(),
    )

    age_s = clamp(state_data.get('age_s'), 0.0, 30.0, 30.0)
    request_rtt_s = time.monotonic() - request_start
    return True, state, age_s, request_rtt_s


def main() -> None:
    parser = argparse.ArgumentParser(description='Hexapod remote polling client')
    parser.add_argument('--endpoint', required=True, help='Full URL to get_command.php')
    parser.add_argument('--token', required=True, help='API token configured on web host')
    parser.add_argument('--serial-port', default='')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--serial-required', action='store_true')
    parser.add_argument('--poll-hz', type=float, default=DEFAULT_POLL_HZ)
    parser.add_argument('--stale-timeout-s', type=float, default=DEFAULT_STALE_TIMEOUT_S)
    parser.add_argument('--http-timeout-s', type=float, default=0.8)
    parser.add_argument('--print-latency', action='store_true', help='Print periodic latency telemetry')
    parser.add_argument('--latency-print-interval-s', type=float, default=1.0)
    parser.add_argument('--receiver-control-hz', type=float, default=50.0, help='Receiver control loop Hz')
    parser.add_argument('--turn-cycle-gain', type=float, default=1.0, help='Scale factor for cycle-based turn heading estimate')
    args = parser.parse_args()

    if args.poll_hz <= 0:
        raise SystemExit('--poll-hz must be > 0')

    if args.serial_port:
        transport: LineTransport = SerialTransport(args.serial_port, args.baud, args.serial_required)
    else:
        print('Serial forwarding disabled (no --serial-port).')
        transport = StdoutTransport()

    controller = HexapodController(transport, event_logs=False)
    dt = 1.0 / args.poll_hz
    last_seen_ok = 0.0
    last_state = ControlState(updated_at=time.time())
    next_latency_print_at = time.time() + max(0.2, args.latency_print_interval_s)
    rtt_ms_samples: list[float] = []
    age_ms_samples: list[float] = []
    connected = False
    last_line = ""
    latency_text = "latency_ms=n/a"
    heading_deg = 0.0
    walk_angle_deg = 0.0
    last_loop_monotonic = time.monotonic()
    turn_cycle_progress = 0.0

    def render_status_line() -> None:
        nonlocal last_line
        mode_text = f"mode={last_state.mode}"
        if not connected:
            mode_text += " (disconnected)"
        if last_state.mode == "walk":
            angle_text = f"walk_angle={walk_angle_deg:+.1f}deg"
        elif last_state.mode == "turn":
            angle_text = f"turn_heading={heading_deg:+.1f}deg(cycle)"
        else:
            angle_text = f"heading={heading_deg:+.1f}deg"
        line = f"{mode_text} | {angle_text} | {latency_text}"
        if line != last_line:
            print(f"\r{line:<80}", end="", flush=True)
            last_line = line

    print(f'Polling {args.endpoint} at {args.poll_hz:.1f} Hz')
    print('Press Ctrl+C to stop')

    try:
        while True:
            start = time.time()
            loop_now_monotonic = time.monotonic()
            dt_s = max(0.0, min(0.2, loop_now_monotonic - last_loop_monotonic))
            last_loop_monotonic = loop_now_monotonic
            ok, fetched_state, remote_age, request_rtt_s = fetch_state(args.endpoint, args.token, args.http_timeout_s)
            now = time.time()
            rtt_ms_samples.append(request_rtt_s * 1000.0)

            if ok and fetched_state is not None:
                if not connected:
                    connected = True
                age_ms_samples.append(remote_age * 1000.0)
                last_seen_ok = now
                stale_remote = remote_age > args.stale_timeout_s
                if stale_remote:
                    last_state.mode = 'stop'
                    last_state.vx = 0.0
                    last_state.vy = 0.0
                    last_state.turn = 0.0
                    last_state.updated_at = now
                else:
                    last_state = fetched_state
                    last_state.updated_at = now
            else:
                offline_too_long = (now - last_seen_ok) > args.stale_timeout_s
                if offline_too_long:
                    if connected:
                        connected = False
                    last_state.mode = 'stop'
                    last_state.vx = 0.0
                    last_state.vy = 0.0
                    last_state.turn = 0.0
                    last_state.updated_at = now

            controller.apply(last_state)
            if abs(last_state.vx) > 0.01 or abs(last_state.vy) > 0.01:
                walk_angle_deg = degrees(atan2(last_state.vy, last_state.vx))
            if last_state.mode == "turn" and connected:
                turn_mag = min(1.0, max(0.0, abs(last_state.turn)))
                speed = min(1.0, max(0.0, last_state.speed))
                # Must mirror servo2040_receiver/main.py mapping for turn_step(step=...)
                step_min = 8.0
                step_max = 32.0
                gait_step = round(step_max - (step_max - step_min) * speed)
                cycle_ticks = max(2.0, 2.0 * (gait_step + 1.0))  # two tripods per full cycle
                cycle_s = cycle_ticks / max(1e-3, args.receiver_control_hz)
                turn_cycle_progress += dt_s / cycle_s

                # Mirror max_angle=10+30*turn_mag, then signed with turn_ratio.
                cycle_delta_deg = (10.0 + 30.0 * turn_mag) * last_state.turn * args.turn_cycle_gain
                while turn_cycle_progress >= 1.0:
                    heading_deg += cycle_delta_deg
                    if heading_deg <= -180.0:
                        heading_deg += 360.0
                    elif heading_deg > 180.0:
                        heading_deg -= 360.0
                    turn_cycle_progress -= 1.0
            else:
                turn_cycle_progress = 0.0

            if args.print_latency and now >= next_latency_print_at and rtt_ms_samples:
                avg_rtt_ms = sum(rtt_ms_samples) / len(rtt_ms_samples)
                avg_age_ms = (sum(age_ms_samples) / len(age_ms_samples)) if age_ms_samples else 0.0
                poll_wait_ms = 1000.0 / (2.0 * args.poll_hz)
                total_latency_ms = avg_rtt_ms + avg_age_ms + poll_wait_ms
                latency_text = f"latency_ms={total_latency_ms:.1f}"
                rtt_ms_samples.clear()
                age_ms_samples.clear()
                next_latency_print_at = now + max(0.2, args.latency_print_interval_s)
            elif not args.print_latency:
                latency_text = "latency_ms=off"

            render_status_line()

            elapsed = time.time() - start
            sleep_s = max(0.0, dt - elapsed)
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        print("")
    finally:
        transport.close()


if __name__ == '__main__':
    main()
