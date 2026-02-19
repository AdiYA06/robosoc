# Internet Controller Deploy Notes

This folder is the internet-facing controller backend/frontend.

## What Is Shared

- Shared UI (both LAN + internet):
  - `../shared_ui/index.html`
  - `../shared_ui/styles.css`
- Internet behavior/auth/lock logic:
  - `app.js`
  - `bootstrap.php`, `set_command.php`, `get_command.php`, `takeover.php`

## Quick Deploy (Git-only flow)

1. Push latest repo updates.
2. Ensure `config.php` exists on server with valid DB credentials and `API_TOKEN`.
3. Run DB/migration endpoint once after backend changes:

```text
https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/init_db.php?api_token=YOUR_API_TOKEN
```

4. Open controller:

```text
https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/
```

## Pi Receiver (internet mode)

```bash
python3 web_controller/pi_remote_client.py \
  --endpoint "https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/web_hosting/get_command.php" \
  --token "YOUR_API_TOKEN" \
  --poll-hz 40 \
  --http-timeout-s 0.4 \
  --stale-timeout-s 1.5 \
  --serial-port /dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e6617c93e39c662b-if00 \
  --baud 115200 \
  --serial-required
```

Optional latency line:

```bash
--print-latency
```

## Notes

- Current gait safety tuning is in `servo2040_receiver/main.py` and applies to both LAN and internet control paths.
- If server/API files changed, run `init_db.php` again to ensure schema is up-to-date.
