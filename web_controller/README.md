# Hexapod Web Controller

This controller can run in two modes:

- Local/LAN mode: quick testing on your home network (no auth)
- Internet mode: remote control from anywhere (requires auth)

## Start (local/LAN)

```bash
python3 web_controller/pi_control_server.py \
  --serial-port /dev/cu.usbmodem2101 \
  --baud 115200 \
  --serial-required
```

Open:

```text
http://<pi-lan-ip>:8080
```

## Start (internet-ready with auth)

Use HTTP Basic auth credentials:

```bash
HEXAPOD_AUTH_USER=robot \
HEXAPOD_AUTH_PASS='change-this-strong-password' \
python3 web_controller/pi_control_server.py \
  --internet \
  --serial-port /dev/cu.usbmodem2101 \
  --baud 115200 \
  --serial-required
```

or explicitly:

```bash
python3 web_controller/pi_control_server.py \
  --internet \
  --auth-user robot \
  --auth-pass 'change-this-strong-password' \
  --serial-port /dev/cu.usbmodem2101 \
  --baud 115200 \
  --serial-required
```

When you open the page, the browser will prompt for username/password first.

## Expose to internet safely

Do not open unauthenticated port forwarding directly.

Recommended options:

1. Cloudflare Tunnel (best for quick secure access, no router port-forward required)
2. Reverse proxy with TLS (Nginx/Caddy) + router forward only `443`

If you still use router forwarding, use internet mode (`--internet`) and a long random password.

## Notes

- Commands auto-stop if connection updates become stale.
- Multi-device lock prevents two controllers from driving at once.
- Keep kill-switch/physical stop available when testing remote control.
