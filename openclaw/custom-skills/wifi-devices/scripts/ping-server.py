#!/usr/bin/env python3
"""ping-server.py — HTTP server for LAN ping + Bluetooth scanning + device DB.
Runs on the Pi host (not in Docker) on port 8888.
Endpoints:
  GET  /scan              → ping all WiFi devices, log results, compact JSON
  GET  /scan?minutes=N    → also include AdGuard DNS activity
  GET  /bt-scan           → discovery + known BT devices, log results
  POST /bt-devices        → add/remove known BT devices (legacy compat)
  GET  /devices           → list all devices (compact)
  POST /devices           → add/update device
  DELETE /devices?id=N    → remove device
  GET  /logs/last-seen    → last detection per device (relative times)
  GET  /logs/presence?hours=24 → presence ranges per device
"""

import json
import os
import sqlite3
import subprocess
import urllib.request
import urllib.error
import base64
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

PORT = 8888
DB_DIR = os.path.expanduser("~/homelab/openclaw/data")
DB_PATH = os.path.join(DB_DIR, "homelab.db")

ADGUARD_URL = os.environ.get("ADGUARD_URL", "http://127.0.0.1:80")
ADGUARD_USER = os.environ.get("ADGUARD_USER", "admin")
ADGUARD_PASS = os.environ.get("ADGUARD_PASS", "changeme")

# Legacy BT devices file (read-only for migration)
BT_DEVICES_FILE = os.path.expanduser(
    "~/homelab/openclaw/custom-skills/wifi-devices/scripts/bt-devices.json"
)

SEED_DEVICES = [
    ("PC-Cristian-WiFi",      "pc",      "cristian", "192.168.1.37", None, None),
    ("PC-Cristian-Ethernet",  "pc",      "cristian", "192.168.1.38", None, None),
    ("Celular-Cristian",      "phone",   "cristian", "192.168.1.40", None, None),
    ("Celular-Roxsy",         "phone",   "roxsy",    "192.168.1.43", None, None),
    ("Desconocido-.48",       "unknown", "unknown",  "192.168.1.48", None, None),
    ("Router-Movistar",       "router",  "unknown",  "192.168.1.1",  None, None),
    ("Raspberry-Pi",          "rpi",     "cristian", "192.168.1.54", None, None),
]


# --- Database ---

def get_db():
    """Get a thread-local DB connection."""
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables and seed data if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'unknown',
            owner TEXT DEFAULT 'unknown',
            wifi_mac TEXT,
            wifi_ip TEXT,
            bt_mac TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY,
            device_id INTEGER REFERENCES devices(id),
            scan_type TEXT NOT NULL,
            detected INTEGER NOT NULL,
            latency_ms REAL,
            rssi INTEGER,
            extra TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_logs_device ON scan_logs(device_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_logs_time ON scan_logs(timestamp);
    """)

    # Seed if empty
    count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO devices (name, type, owner, wifi_ip, wifi_mac, bt_mac) VALUES (?,?,?,?,?,?)",
            SEED_DEVICES,
        )
        # Migrate BT devices from legacy JSON if exists
        try:
            with open(BT_DEVICES_FILE, "r") as f:
                bt_devs = json.load(f)
            for mac, name in bt_devs.items():
                row = conn.execute("SELECT id FROM devices WHERE name = ?", (name,)).fetchone()
                if row:
                    conn.execute("UPDATE devices SET bt_mac = ? WHERE id = ?", (mac.upper(), row["id"]))
                else:
                    conn.execute(
                        "INSERT INTO devices (name, type, owner, bt_mac) VALUES (?, 'unknown', 'unknown', ?)",
                        (name, mac.upper()),
                    )
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        conn.commit()
    conn.close()


def get_wifi_devices():
    """Get devices with wifi_ip set."""
    conn = get_db()
    rows = conn.execute("SELECT id, name, wifi_ip FROM devices WHERE wifi_ip IS NOT NULL").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bt_devices():
    """Get devices with bt_mac set."""
    conn = get_db()
    rows = conn.execute("SELECT id, name, bt_mac FROM devices WHERE bt_mac IS NOT NULL").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_scans_batch(entries):
    """Insert multiple scan log entries at once. Timestamp in local time."""
    now = datetime.now().isoformat()
    conn = get_db()
    conn.executemany(
        "INSERT INTO scan_logs (device_id, scan_type, detected, latency_ms, rssi, extra, timestamp) VALUES (?,?,?,?,?,?,?)",
        [(*e, now) for e in entries],
    )
    conn.commit()
    conn.close()


# --- Relative time helper ---

def relative_time(iso_str):
    """Convert ISO timestamp to relative string like 'hace 5min'."""
    if not iso_str:
        return "nunca"
    try:
        ts = datetime.fromisoformat(iso_str)
        now = datetime.now()
        diff = now - ts
        secs = int(diff.total_seconds())
        if secs < 60:
            return "hace <1min"
        elif secs < 3600:
            return f"hace {secs // 60}min"
        elif secs < 86400:
            return f"hace {secs // 3600}h"
        else:
            return f"hace {secs // 86400}d"
    except Exception:
        return iso_str


# --- WiFi / Ping ---

def ping_ip(ip):
    """Ping a single IP. Returns (ip, alive, latency_ms)."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True, text=True, timeout=3,
        )
        alive = result.returncode == 0
        latency = None
        if alive:
            for line in result.stdout.split("\n"):
                if "time=" in line:
                    latency = float(line.split("time=")[1].split()[0])
                    break
        return ip, alive, latency
    except (subprocess.TimeoutExpired, Exception):
        return ip, False, None


def scan_all():
    """Ping all WiFi devices from DB, log results, return compact JSON."""
    devices = get_wifi_devices()

    results = []
    with ThreadPoolExecutor(max_workers=max(len(devices), 1)) as pool:
        futures = {pool.submit(ping_ip, d["wifi_ip"]): d for d in devices}
        for future in as_completed(futures):
            dev = futures[future]
            ip, alive, latency = future.result()
            results.append({
                "id": dev["id"],
                "name": dev["name"],
                "ip": ip,
                "alive": alive,
                "latency_ms": latency,
            })

    results.sort(key=lambda d: [int(x) for x in d["ip"].split(".")])

    # Log to DB
    log_entries = [
        (r["id"], "wifi", 1 if r["alive"] else 0, r["latency_ms"], None, None)
        for r in results
    ]
    if log_entries:
        log_scans_batch(log_entries)

    # Compact response
    online = []
    offline = []
    for r in results:
        if r["alive"]:
            lat = f" ({r['latency_ms']:.0f}ms)" if r["latency_ms"] else ""
            online.append(f"{r['name']}{lat}")
        else:
            offline.append(r["name"])

    return {
        "online": online,
        "offline": offline,
        "count": f"{len(online)}/{len(results)}",
    }


def get_querylog_compact(minutes=30):
    """Fetch DNS activity from AdGuard, return compact format."""
    try:
        url = f"{ADGUARD_URL}/control/querylog?limit=500"
        credentials = base64.b64encode(
            f"{ADGUARD_USER}:{ADGUARD_PASS}".encode()
        ).decode()
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {credentials}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        # Build IP->device_name mapping from DB
        devices = get_wifi_devices()
        ip_to_name = {d["wifi_ip"]: d["name"] for d in devices}

        activity = {}
        for entry in data.get("data", []):
            client = entry.get("client", "")
            if client in ip_to_name:
                name = ip_to_name[client]
                if name not in activity:
                    activity[name] = {"q": 0, "top": {}}
                activity[name]["q"] += 1
                domain = entry.get("question", {}).get("name", "")
                if domain:
                    activity[name]["top"][domain] = activity[name]["top"].get(domain, 0) + 1

        # Compact: "Celular-Cristian: 45q (youtube.com, google.com)"
        result = []
        for name, info in sorted(activity.items()):
            top3 = sorted(info["top"].items(), key=lambda x: x[1], reverse=True)[:3]
            domains = ", ".join(d for d, _ in top3)
            result.append(f"{name}: {info['q']}q ({domains})")
        return result
    except Exception as e:
        return [f"error: {e}"]


# --- Bluetooth ---

def bt_get_info(mac):
    """Get BT device info (RSSI, Icon) via bluetoothctl info before removing."""
    info = {}
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", mac],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("RSSI:"):
                m = re.search(r"\((-?\d+)\)", line)
                if m:
                    info["rssi"] = int(m.group(1))
            elif line.startswith("Icon:"):
                info["icon"] = line.split(":", 1)[1].strip()
            elif line.startswith("Class:"):
                info["class"] = line.split(":", 1)[1].strip()
    except Exception:
        pass
    return info


def check_bt_device(mac):
    """Check if a known BT device is nearby using hcitool name."""
    try:
        result = subprocess.run(
            ["hcitool", "name", mac],
            capture_output=True, text=True, timeout=6,
        )
        name = result.stdout.strip()
        return name if name else None
    except (subprocess.TimeoutExpired, Exception):
        return None


def bt_discovery_scan(duration=8):
    """Run BT discovery scan. Returns list of {mac, name, info}."""
    discovered = []
    try:
        proc = subprocess.Popen(
            ["bluetoothctl", "--timeout", str(duration), "scan", "on"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        proc.wait(timeout=duration + 5)

        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=3,
        )
        for line in result.stdout.strip().split("\n"):
            match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line)
            if match:
                mac = match.group(1)
                name = match.group(2)
                info = bt_get_info(mac)
                discovered.append({"mac": mac, "name": name, "info": info})
    except (subprocess.TimeoutExpired, Exception):
        pass

    # Clean up discovered (non-paired) devices
    try:
        for dev in discovered:
            subprocess.run(
                ["bluetoothctl", "remove", dev["mac"]],
                capture_output=True, timeout=3,
            )
    except Exception:
        pass

    return discovered


def bt_scan_all():
    """Full BT scan: discovery + known devices check. Log + compact JSON."""
    known = get_bt_devices()
    known_macs = {d["bt_mac"].upper(): d for d in known}

    discovery_result = []
    known_results = []

    def do_discovery():
        nonlocal discovery_result
        discovery_result = bt_discovery_scan(8)

    def do_known_checks():
        nonlocal known_results
        if not known:
            return
        with ThreadPoolExecutor(max_workers=min(len(known), 4)) as pool:
            futures = {pool.submit(check_bt_device, d["bt_mac"]): d for d in known}
            for future in as_completed(futures):
                dev = futures[future]
                detected_name = future.result()
                known_results.append({
                    "id": dev["id"],
                    "name": dev["name"],
                    "mac": dev["bt_mac"],
                    "nearby": detected_name is not None,
                })

    t1 = threading.Thread(target=do_discovery)
    t2 = threading.Thread(target=do_known_checks)
    t1.start()
    t2.start()
    t1.join(timeout=20)
    t2.join(timeout=20)

    # Log known device results
    log_entries = []
    for r in known_results:
        rssi = None
        extra = None
        for disc in discovery_result:
            if disc["mac"].upper() == r["mac"].upper() and disc.get("info"):
                rssi = disc["info"].get("rssi")
                extra = disc["info"]
                break
        log_entries.append((
            r["id"], "bt", 1 if r["nearby"] else 0,
            None, rssi,
            json.dumps(extra, ensure_ascii=False) if extra else None,
        ))
    if log_entries:
        log_scans_batch(log_entries)

    # Compact response
    nearby = [r["name"] for r in known_results if r["nearby"]]
    not_detected = [r["name"] for r in known_results if not r["nearby"]]

    new_discovered = []
    for d in discovery_result:
        if d["mac"].upper() not in known_macs:
            rssi = d["info"].get("rssi", "")
            rssi_str = f" ({rssi}dBm)" if rssi else ""
            new_discovered.append(f"{d['name']} [{d['mac']}]{rssi_str}")

    result = {"count": f"{len(nearby)}/{len(known_results)}"}
    if nearby:
        result["nearby"] = nearby
    if not_detected:
        result["not_detected"] = not_detected
    if new_discovered:
        result["discovered"] = new_discovered
    return result


# --- Logs / History ---

def get_last_seen():
    """Last detection per device with relative times."""
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, d.name, d.wifi_ip, d.bt_mac,
            (SELECT MAX(sl.timestamp) FROM scan_logs sl
             WHERE sl.device_id = d.id AND sl.scan_type = 'wifi' AND sl.detected = 1) as wifi_last,
            (SELECT MAX(sl.timestamp) FROM scan_logs sl
             WHERE sl.device_id = d.id AND sl.scan_type = 'bt' AND sl.detected = 1) as bt_last
        FROM devices d ORDER BY d.name
    """).fetchall()
    conn.close()

    devices = []
    for r in rows:
        entry = {"name": r["name"]}
        if r["wifi_ip"]:
            entry["wifi"] = relative_time(r["wifi_last"])
        if r["bt_mac"]:
            entry["bt"] = relative_time(r["bt_last"])
        devices.append(entry)

    return {"devices": devices}


def get_presence(hours=24):
    """Presence ranges per device in the last N hours."""
    conn = get_db()
    since = (datetime.now() - timedelta(hours=hours)).isoformat()

    rows = conn.execute("""
        SELECT d.name, sl.timestamp
        FROM scan_logs sl
        JOIN devices d ON sl.device_id = d.id
        WHERE sl.timestamp >= ? AND sl.detected = 1
        ORDER BY d.name, sl.timestamp
    """, (since,)).fetchall()
    conn.close()

    # Group by device
    device_times = {}
    for r in rows:
        name = r["name"]
        if name not in device_times:
            device_times[name] = []
        device_times[name].append(r["timestamp"])

    # Build ranges: group detections within 15min gaps
    result = []
    for name in sorted(device_times.keys()):
        times = device_times[name]
        if not times:
            continue
        ranges = []
        range_start = datetime.fromisoformat(times[0])
        range_end = range_start
        for t in times[1:]:
            ts = datetime.fromisoformat(t)
            if (ts - range_end).total_seconds() > 900:  # 15min gap
                ranges.append((range_start, range_end))
                range_start = ts
            range_end = ts
        ranges.append((range_start, range_end))

        range_strs = []
        for s, e in ranges:
            start_str = s.strftime("%H:%M")
            if (datetime.now() - e).total_seconds() < 300:
                end_str = "ahora"
            else:
                end_str = e.strftime("%H:%M")
            range_strs.append(f"{start_str}-{end_str}")

        result.append(f"{name}: {', '.join(range_strs)}")

    return {"today": result} if result else {"today": ["sin datos"]}


def get_all_devices_compact():
    """List all devices in compact format."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, type, owner, wifi_ip, wifi_mac, bt_mac FROM devices ORDER BY name"
    ).fetchall()
    conn.close()

    devices = []
    for r in rows:
        d = {"id": r["id"], "name": r["name"]}
        if r["type"] != "unknown":
            d["type"] = r["type"]
        if r["owner"] != "unknown":
            d["owner"] = r["owner"]
        if r["wifi_ip"]:
            d["ip"] = r["wifi_ip"]
        if r["wifi_mac"]:
            d["wifi_mac"] = r["wifi_mac"]
        if r["bt_mac"]:
            d["bt_mac"] = r["bt_mac"]
        devices.append(d)
    return {"devices": devices, "total": len(devices)}


def add_or_update_device(data):
    """Add or update a device. Returns (status_code, result_dict)."""
    name = data.get("name", "").strip()
    if not name:
        return 400, {"error": "name required"}

    conn = get_db()
    existing = conn.execute("SELECT id FROM devices WHERE name = ?", (name,)).fetchone()

    if existing:
        fields = []
        values = []
        for col in ("type", "owner", "wifi_ip", "wifi_mac", "bt_mac"):
            if col in data:
                fields.append(f"{col} = ?")
                values.append(data[col])
        if fields:
            values.append(existing["id"])
            conn.execute(f"UPDATE devices SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        conn.close()
        return 200, {"result": f"updated {name}"}
    else:
        conn.execute(
            "INSERT INTO devices (name, type, owner, wifi_ip, wifi_mac, bt_mac) VALUES (?,?,?,?,?,?)",
            (name, data.get("type", "unknown"), data.get("owner", "unknown"),
             data.get("wifi_ip"), data.get("wifi_mac"), data.get("bt_mac")),
        )
        conn.commit()
        conn.close()
        return 201, {"result": f"added {name}"}


def delete_device(device_id):
    """Delete a device and its logs."""
    conn = get_db()
    dev = conn.execute("SELECT name FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not dev:
        conn.close()
        return 404, {"error": f"device {device_id} not found"}
    conn.execute("DELETE FROM scan_logs WHERE device_id = ?", (device_id,))
    conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    conn.commit()
    conn.close()
    return 200, {"result": f"deleted {dev['name']}"}


# --- HTTP Handler ---

class ScanHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/scan":
            minutes = int(params.get("minutes", [0])[0])
            result = scan_all()
            if minutes > 0:
                result["dns"] = get_querylog_compact(minutes)
            self._json_response(200, result)

        elif parsed.path == "/bt-scan":
            result = bt_scan_all()
            self._json_response(200, result)

        elif parsed.path == "/bt-devices":
            devices = get_bt_devices()
            self._json_response(200, {
                "devices": {d["bt_mac"]: d["name"] for d in devices},
            })

        elif parsed.path == "/devices":
            self._json_response(200, get_all_devices_compact())

        elif parsed.path == "/logs/last-seen":
            self._json_response(200, get_last_seen())

        elif parsed.path == "/logs/presence":
            hours = int(params.get("hours", [24])[0])
            self._json_response(200, get_presence(hours))

        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if parsed.path == "/bt-devices":
            action = body.get("action")
            mac = body.get("mac", "").upper()
            name = body.get("name", "")

            if not mac or not action:
                self._json_response(400, {"error": "need action and mac"})
                return

            if action == "add":
                if not name:
                    self._json_response(400, {"error": "need name"})
                    return
                code, result = add_or_update_device({"name": name, "bt_mac": mac})
                self._json_response(code, result)

            elif action == "remove":
                conn = get_db()
                dev = conn.execute(
                    "SELECT id, name FROM devices WHERE bt_mac = ?", (mac,)
                ).fetchone()
                if dev:
                    conn.execute("UPDATE devices SET bt_mac = NULL WHERE id = ?", (dev["id"],))
                    conn.commit()
                    conn.close()
                    self._json_response(200, {"result": f"removed BT from {dev['name']}"})
                else:
                    conn.close()
                    self._json_response(404, {"error": f"MAC {mac} not found"})
            else:
                self._json_response(400, {"error": f"unknown action: {action}"})

        elif parsed.path == "/devices":
            code, result = add_or_update_device(body)
            self._json_response(code, result)

        else:
            self._json_response(404, {"error": "not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/devices":
            dev_id = params.get("id", [None])[0]
            if not dev_id:
                self._json_response(400, {"error": "need id param"})
                return
            code, result = delete_device(int(dev_id))
            self._json_response(code, result)
        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    init_db()
    print(f"ping-server listening on 0.0.0.0:{PORT} (DB: {DB_PATH})")
    server = HTTPServer(("0.0.0.0", PORT), ScanHandler)
    server.serve_forever()
