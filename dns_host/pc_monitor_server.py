#!/usr/bin/env python3
"""Pings hosts listed in computers.json and serves the results as JSON
for the Vobot Mini Dock "PC Monitor" app. Stdlib only."""
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_FILE = os.environ.get("PCMON_CONFIG", "/opt/vobot-monitor/computers.json")
PORT = int(os.environ.get("PCMON_PORT", "8088"))
INTERVAL = int(os.environ.get("PCMON_INTERVAL", "30"))

_status = {"updated": 0, "online": 0, "total": 0, "computers": [], "error": None}
_lock = threading.Lock()


def log(msg):
    print(f"[{time.strftime('%X')}] {msg}", flush=True)


def load_computers(path):
    """Read host definitions from JSON file. Re-read every cycle so edits apply live."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("computers", []), None
    except FileNotFoundError:
        return [], f"config not found: {path}"
    except (json.JSONDecodeError, OSError) as err:
        return [], f"config error: {err}"


def ping(target):
    if not target:
        return False
    res = subprocess.run(["ping", "-c", "1", "-W", "1", target],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def check(comp):
    """Try hostname first, then fall back to the IP (mDNS .local can be flaky)."""
    up = False
    for t in (comp.get("target"), comp.get("ip")):
        if t and ping(t):
            up = True
            break
    return {
        "name": comp.get("name", "unk"),
        "description": comp.get("description", ""),
        "ip": comp.get("ip", ""),
        "up": up,
    }


def poll_loop():
    with ThreadPoolExecutor(max_workers=8) as pool:
        while True:
            computers, err = load_computers(CONFIG_FILE)
            results = list(pool.map(check, computers))
            online = sum(1 for r in results if r["up"])
            with _lock:
                _status.update(updated=int(time.time()), online=online,
                               total=len(results), computers=results, error=err)
            down = [r["name"] for r in results if not r["up"]]
            log(err or f"{online}/{len(results)} up" + (f", down: {','.join(down)}" if down else ""))
            time.sleep(INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/", "/status"):
            self.send_error(404)
            return
        with _lock:
            body = json.dumps(_status).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    log(f"PC Monitor: config={CONFIG_FILE} port={PORT} interval={INTERVAL}s")
    threading.Thread(target=poll_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
