# Vobot PC Monitor

Shows on a Vobot Mini Dock which of your home computers can be reached.

```
┌──────────────────────────┐   HTTP GET /status   ┌──────────────────────┐
│ DNS machine (Pi-hole)    │ ◄─────────────────── │ Vobot Mini Dock      │
│ pc_monitor_server.py     │   JSON every 15 s    │ "PC Monitor" app     │
│ pings hosts every 30 s   │ ───────────────────► │ x/y up, DOWN first   │
└──────────────────────────┘                      └──────────────────────┘
```

- **`dns_host/`** is a small Python service that uses only the standard library. It reads `computers.json` and pings each host, trying the `target` hostname first and then the `ip`. It serves the results at `http://<dns-ip>:8088/status`.
- **`vobot_app/pc_monitor/`** is a MicroPython/LVGL app for the dock. It reads that URL and shows the online count, which is green when every host is up and red when any is down. Hosts that are down are listed first.

## Configuring the computers

Edit `computers.json`. On the DNS machine it lives at `/opt/vobot-monitor/computers.json`. The service reads the file again on every cycle, so you don't need to restart it.

```json
{
  "computers": [
    { "name": "tembo", "target": "tembo.local", "ip": "10.0.10.73", "description": "Primary Desktop" }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Short label shown on the dock (keep it under 10 characters) |
| `target` | no | Hostname to ping first, e.g. `host.local` |
| `ip` | no | Fallback address. You need at least one of `target` or `ip` |
| `description` | no | Shown next to the name |

## Deploying

### 1. DNS machine (Linux with systemd)

```bash
scp -r dns_host pi@10.0.10.12:~
ssh pi@10.0.10.12 'sudo ~/dns_host/install.sh'
```

The installer copies the files to `/opt/vobot-monitor`, sets up and starts `vobot-pc-monitor.service`, and prints the current status. On a reinstall it keeps any existing `computers.json`. To push an updated host list:

```bash
scp computers.json pi@10.0.10.12:/tmp/ && ssh pi@10.0.10.12 'sudo cp /tmp/computers.json /opt/vobot-monitor/'
```

You can change the settings through environment variables in the unit file: `PCMON_CONFIG`, `PCMON_PORT` (default 8088) and `PCMON_INTERVAL` (default 30 seconds).

### 2. Vobot Mini Dock

1. Turn on Developer Mode on the dock, then power-cycle it.
2. Connect it by USB-C, open Thonny and select the ESP32 port.
3. Under **View → Files**, upload the `vobot_app/pc_monitor` folder into the device's `/apps` folder.
4. Press **Ctrl+D** to restart.
5. Optional: if the DNS machine isn't at `10.0.10.12`, change **Status URL** in the dock's web settings for "PC Monitor".

## Troubleshooting

| Symptom | Check |
|---|---|
| Dock shows `Server unreachable` | `curl http://10.0.10.12:8088/status` from another machine; check the firewall on port 8088 |
| Dock shows `No Wi-Fi` | The dock's network connection |
| A host is always DOWN | Its `.local` name may not resolve on the Pi (install `avahi-daemon`) or its `ip` may be wrong |
| Service problems | `journalctl -u vobot-pc-monitor -f` |
| App doesn't appear on the dock | The folder must be `/apps/pc_monitor/__init__.py`, not nested one level deeper. Check the Thonny log |

## Testing locally

```bash
PCMON_CONFIG=computers.json PCMON_PORT=18088 PCMON_INTERVAL=5 python3 dns_host/pc_monitor_server.py
curl localhost:18088/status
```

`vobot_pc_monitor_and_push.py` is the old design, which pushed messages to the dock directly. It is kept only for reference.
