# Web Hosting Package (University Server)

Upload everything in this folder to:

`https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/`

## 1) Configure

1. Copy `config.php.example` to `config.php`
2. Fill your DB password and set a long random `API_TOKEN`

## 2) Initialize DB table

Open in browser once:

`https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/init_db.php?api_token=YOUR_TOKEN`

You should see JSON with `"ok": true`.
Run this again after backend updates; it also applies schema migrations.

## 3) Open controller UI

Open:

`https://web.cs.manchester.ac.uk/c59506kl/hexapod_robot/`

Paste the same API token in the token field and press `Use Token`.

## Files

- `index.html`, `app.js`, `styles.css`: remote control UI
- `set_command.php`: writes latest command into MySQL
- `get_command.php`: returns latest command JSON for the Pi
- `takeover.php`: force lock ownership to this client
- `init_db.php`: creates the `hexapod_command` table
