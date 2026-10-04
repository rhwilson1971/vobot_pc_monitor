#!/usr/bin/env python3
import json
import os
import subprocess
import time
import requests

CONFIG_FILE = "/opt/vobot-monitor/computers.json"

# Vobot Mini Dock endpoint
VOBOT_IP = "10.0.10.53"
VOBOT_API_URL = f"http://{VOBOT_IP}/api/v1/custom_message"

def load_computers(config_path: str) -> list:
    """Read host definitions from JSON file."""
    if not os.path.exists(config_path):
        print(f"[{time.strftime('%X')}] Config {config_path} not found.")
        return []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("computers", [])
    except json.JSONDecodeError as err:
        print(f"[{time.strftime('%X')}] Error decoding JSON: {err}")
        return []

def ping_host(host_target: str) -> bool:
    """Send a fast 1-second timeout ping using Linux ping."""
    cmd = ["ping", "-c", "1", "-W", "1", host_target]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0

def push_to_vobot(all_up: bool, online_count: int, total_count: int, failed_hosts: list):
    """Deliver formatted payload to the Vobot Mini Dock."""
    if total_count == 0:
        text = "NO HOSTS"
        color = "#FFA500"
    elif all_up:
        text = f"ALL ON ({online_count}/{total_count})"
        color = "#00FF00"
    else:
        text = f"DOWN: {','.join(failed_hosts)}"
        color = "#FF3300"

    payload = {
        "text": text,
        "color": color,
        "duration": 15,
        "scroll": len(text) > 8
    }

    try:
        requests.post(VOBOT_API_URL, json=payload, timeout=3)
    except requests.exceptions.RequestException:
        pass

def main():
    print(f"Vobot Fleet Monitor active. Target dock: {VOBOT_IP}")
    while True:
        computers = load_computers(CONFIG_FILE)

        if not computers:
            push_to_vobot(False, 0, 0, [])
            time.sleep(30)
            continue

        failed = []
        for comp in computers:
            name = comp.get("name", "unk")
            target = comp.get("target") or comp.get("ip")
            
            if not target or not ping_host(target):
                failed.append(name)

        total_count = len(computers)
        online_count = total_count - len(failed)
        all_up = (len(failed) == 0)

        push_to_vobot(all_up, online_count, total_count, failed)
        time.sleep(30)

if __name__ == "__main__":
    main()
