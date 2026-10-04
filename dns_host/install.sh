#!/usr/bin/env bash
# Run on the DNS machine (Pi-hole host): sudo ./install.sh
set -euo pipefail
cd "$(dirname "$0")"
install -d /opt/vobot-monitor
install -m 755 pc_monitor_server.py /opt/vobot-monitor/
# Don't clobber an edited host list on reinstall
[ -f /opt/vobot-monitor/computers.json ] || install -m 644 computers.json /opt/vobot-monitor/
install -m 644 vobot-pc-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vobot-pc-monitor
sleep 2
curl -s http://127.0.0.1:8088/status || true
echo
echo "Installed. Edit /opt/vobot-monitor/computers.json (picked up on next cycle)."
