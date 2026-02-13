# Internet Control Version (Separate Folder)

This folder is a separate internet-enabled control path. Your existing local setup remains unchanged.

## Components

- `relay_server.py` (public server):
  - hosts web UI
  - authenticates users by shared token
  - enforces single controller lock with lease timeout
  - exposes `/api/poll` for Pi bridge

- `pi_bridge.py` (run on Raspberry Pi or Mac acting as Pi):
  - polls relay server
  - forwards latest command to Servo 2040 over USB serial

- `static/*`:
  - remote control webpage (joystick + keyboard)

## 1) Run relay server (public machine)

```bash
cd /Users/david673/Library/CloudStorage/OneDrive-TheUniversityofManchester/Desktop/Manchester/RoboSoc_Spider
python3 internet_controller/relay_server.py --token "CHANGE_ME" --port 8090
```

Open UI:
- `http://<server-ip-or-domain>:8090`

## 2) Run bridge on Pi (or Mac test)

Install serial dependency:

```bash
pip3 install pyserial
```

Run bridge:

```bash
python3 internet_controller/pi_bridge.py \
  --relay "http://<server-ip-or-domain>:8090" \
  --serial-port /dev/ttyACM0 \
  --baud 115200
```

On macOS, serial port is usually `/dev/cu.usbmodem*`.

## 3) Servo 2040 side

Keep using your existing receiver program in:
- `/Users/david673/Library/CloudStorage/OneDrive-TheUniversityofManchester/Desktop/Manchester/RoboSoc_Spider/servo2040_receiver/main.py`

## Security notes

This is a practical baseline, not production-hardening.
For real internet exposure, add:

1. HTTPS reverse proxy (Nginx/Caddy + TLS)
2. Strong auth (not just shared token)
3. Rate limiting and audit logs
4. Network/firewall allowlist for bridge/poll endpoints

