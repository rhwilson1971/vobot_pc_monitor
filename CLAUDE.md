# CLAUDE.md

Vobot PC Monitor has two parts that communicate over HTTP. See README.md for how to deploy it.

## Layout
- `dns_host/pc_monitor_server.py`: CPython 3 service for the DNS machine (a Raspberry Pi running Pi-hole, `jina`, 10.0.10.12). **Standard library only.** Don't add pip dependencies.
- `dns_host/install.sh` and `vobot-pc-monitor.service`: deploy to `/opt/vobot-monitor` and run under systemd with `DynamicUser=yes`.
- `dns_host/computers.json`: the template host list. `./computers.json` at the repo root is the user's working copy. Keep the two in sync.
- `vobot_app/pc_monitor/`: the Mini Dock app. **MicroPython + LVGL 9.1**, not CPython.
- `vobot_pc_monitor_and_push.py`: the old push-based design, kept for reference only. Don't extend it.

## Contract between the two parts (keep both sides in sync)
`GET /status` (and `/`) returns:
```json
{"updated": <unix>, "online": int, "total": int, "error": str|null,
 "computers": [{"name": str, "description": str, "ip": str, "up": bool}]}
```
If you add a field, add it on the server first and read it on the dock with `.get()` and a default, so an older dock app or server doesn't break.

## Vobot app rules (MicroPython)
- The entrypoint is `__init__.py` and it must define `NAME = "PC Monitor"`. Never add a `main.py`.
- Resource paths must be `f"A:apps/{NAME}/resources/..."`, because the device may rename the folder to match `NAME`.
- Use `urequests` (always `close()` the response) and `lv.KEY.*` constants. Only use fonts the device provides (`lv.font_ascii_14/18/22`, `lv.font_ascii_bold_22`, ...).
- The screen is 320x240. MicroPython has no `dataclasses`, `typing` or `requests`. Prefer `%` formatting for the safest compatibility.
- `on_running_foreground` runs about every 200 ms. Network calls are blocking, so keep the poll gated by `POLL_SECONDS` and `timeout=3`.
- `on_stop` must be idempotent (the app is entered and exited repeatedly).
- User settings go through `get_settings_json()` and are read with `app_mgr.config()`.
- The installed app has a 200 KB limit.

## Checking changes
```bash
python3 -m py_compile dns_host/pc_monitor_server.py vobot_app/pc_monitor/__init__.py
PCMON_CONFIG=computers.json PCMON_PORT=18088 PCMON_INTERVAL=5 python3 dns_host/pc_monitor_server.py &
sleep 6; curl -s localhost:18088/status; kill %1
```
The dock app can't run on CPython because `lvgl` isn't available. Check it with the Mini Dock emulator or on the device through Thonny (upload to `/apps`, then Ctrl+D). Delete any `__pycache__/` folders before uploading or copying.

## Known data issues
- `saa` and `tafuta` both use `10.0.10.54`. One of them is probably wrong.
- `jina` targets `127.0.0.1`, so it always reports as up.
