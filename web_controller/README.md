# Web Controller + Raspberry Pi Receiver

This folder gives you a complete control signal path:

1. Browser UI (phone/laptop) acts as your robot controller.
2. Raspberry Pi hosts the UI and receives control JSON.
3. A fixed-rate loop reads the latest command and applies it to your robot logic.

## Run on Raspberry Pi

```bash
cd /Users/david673/Library/CloudStorage/OneDrive-TheUniversityofManchester/Desktop/Manchester/RoboSoc_Spider
python3 web_controller/pi_control_server.py
```

The server starts on port `8080`.
Open this on any device in the same Wi-Fi network:

- `http://<pi-ip>:8080`

Find Pi IP with:

```bash
hostname -I
```

## Command format

The UI sends this JSON every 100 ms to `/api/control`:

```json
{
  "mode": "walk",
  "vx": 0.5,
  "vy": -0.2,
  "turn": 0.1,
  "speed": 0.7,
  "height": -0.1
}
```

Ranges:

- `vx`, `vy`, `turn`: `-1.0` to `1.0`
- `speed`: `0.0` to `1.0`
- `height`: `-1.0` to `1.0`

If no new command arrives for `0.7s`, server auto-failsafe to stop.

## Integrate with your hexapod code

Edit `HexapodController.apply()` in:

- `web_controller/pi_control_server.py`

That method is where you map incoming `mode/vx/vy/turn/speed/height` to your gait calls.

Suggested mapping:

- `mode="walk"`: translate `vx/vy` into step direction and speed.
- `mode="turn"`: use `turn` to choose left/right turning rate.
- `mode="stance"`: hold position and adjust body height.
- `mode="stop"`: neutral pose / all zeros.

## Next hardware step

Since your servo board is Servo 2040 (RP2040), common architecture is:

1. Raspberry Pi runs this web control server.
2. Pi sends high-level commands to Servo 2040 over UART/I2C/USB serial.
3. Servo 2040 runs low-level servo timing + IK execution.

You can keep this web protocol unchanged while replacing only the `apply()` internals.
