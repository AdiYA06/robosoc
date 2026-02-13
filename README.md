# Hexapod Web Control Quick Start

## 1. Detect Servo Board Serial Port

### macOS
```bash
ls /dev/cu.usbmodem*
```

### Raspberry Pi / Linux
```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Use the detected device path in the commands below.

## 2. Internet Web Control (University Hosting)

### Health / DB init check
Open:
[init_db.php](https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/init_db.php?api_token=97af9d5e3b1287eb4b1f1266820f9dbaaf49f57c137e9c30ac339952217e4582)

### Controller URL
Open:
[web controller](https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/)

### Pi (or machine with servo connected) receiver
```bash
python3 web_controller/pi_remote_client.py \
  --endpoint "https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/get_command.php" \
  --token "97af9d5e3b1287eb4b1f1266820f9dbaaf49f57c137e9c30ac339952217e4582" \
  --serial-port /dev/ttyACM0 \
  --baud 115200 \
  --serial-required
```

Note:
- On macOS, serial port may look like `/dev/cu.usbmodem2101`.
- On Raspberry Pi, serial port is usually `/dev/ttyACM0` or `/dev/ttyUSB0`.

## 3. Local Web Control (LAN)

### Get local IP

#### macOS
```bash
ipconfig getifaddr en0
```

#### Raspberry Pi / Linux
```bash
hostname -I
```

### Run local receiver server
```bash
python3 web_controller/pi_control_server.py \
  --serial-port /dev/ttyACM0 \
  --baud 115200 \
  --serial-required
```

Then open:

`http://<local-ip>:8080`

## Security

- Do not commit real API tokens/passwords into public repos.
- Keep `web_hosting/config.php` secret in production.
