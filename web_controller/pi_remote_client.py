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
    parser.add_argument('--latency-print-interval-s', type=float, default=1.0)
    args = parser.parse_args()

    if args.poll_hz <= 0:
        raise SystemExit('--poll-hz must be > 0')

    if args.serial_port:
        transport: LineTransport = SerialTransport(args.serial_port, args.baud, args.serial_required)
    else:
        print('Serial forwarding disabled (no --serial-port).')
        transport = StdoutTransport()

    controller = HexapodController(transport)
    dt = 1.0 / args.poll_hz
    last_seen_ok = 0.0
    last_state = ControlState(updated_at=time.time())
    next_latency_print_at = time.time() + max(0.2, args.latency_print_interval_s)
    rtt_ms_samples: list[float] = []
    age_ms_samples: list[float] = []
    ok_count = 0
    fail_count = 0

    print(f'Polling {args.endpoint} at {args.poll_hz:.1f} Hz')
    print('Press Ctrl+C to stop')

    try:
        while True:
            start = time.time()
            ok, fetched_state, remote_age, request_rtt_s = fetch_state(args.endpoint, args.token, args.http_timeout_s)
            now = time.time()
            rtt_ms_samples.append(request_rtt_s * 1000.0)

            if ok and fetched_state is not None:
                ok_count += 1
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
                fail_count += 1
                offline_too_long = (now - last_seen_ok) > args.stale_timeout_s
                if offline_too_long:
                    last_state.mode = 'stop'
                    last_state.vx = 0.0
                    last_state.vy = 0.0
                    last_state.turn = 0.0
                    last_state.updated_at = now

            controller.apply(last_state)

            if now >= next_latency_print_at and rtt_ms_samples:
                avg_rtt_ms = sum(rtt_ms_samples) / len(rtt_ms_samples)
                avg_age_ms = (sum(age_ms_samples) / len(age_ms_samples)) if age_ms_samples else 0.0
                poll_wait_ms = 1000.0 / (2.0 * args.poll_hz)
                total_latency_ms = avg_rtt_ms + avg_age_ms + poll_wait_ms
                print(f"total_latency_ms={total_latency_ms:.1f}")
                rtt_ms_samples.clear()
                age_ms_samples.clear()
                ok_count = 0
                fail_count = 0
                next_latency_print_at = now + max(0.2, args.latency_print_interval_s)

            elapsed = time.time() - start
            sleep_s = max(0.0, dt - elapsed)
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()


if __name__ == '__main__':
    main()
