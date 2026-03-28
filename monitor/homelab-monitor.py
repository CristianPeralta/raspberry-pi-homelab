#!/usr/bin/env python3
"""homelab-monitor.py — Proactive notification system for homelab.
Compares WiFi scan results against previous state and sends Telegram alerts
for arrivals, departures, idle devices, and blocked DNS queries.

Runs via cron after each WiFi scan (every 5 min).
"""

import json
import os
import sqlite3
import urllib.request
import urllib.error
import base64
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/homelab/openclaw/data/homelab.db")

ADGUARD_URL = os.environ.get("ADGUARD_URL", "http://127.0.0.1:80")
ADGUARD_USER = os.environ.get("ADGUARD_USER", "admin")
ADGUARD_PASS = os.environ.get("ADGUARD_PASS", "changeme")

CONFIG = {
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
    "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
    "monitor_devices": ["Celular-Cachi", "Celular-Roxsy", "Celular-Cristian"],
    "events": {
        "arrival": True,
        "departure": True,
        "idle_minutes": 60,
        "dns_categories": [
            "FilteredSafeBrowsing",
            "FilteredParental",
            "FilteredBlockedService",
        ],
    },
    "cooldowns": {
        "arrival": 1800,   # 30 min
        "departure": 1800,
        "idle": 7200,      # 2 hours
        "dns": 600,        # 10 min
    },
}

OWNER_NAMES = {
    "cristian": "Cristian",
    "roxsy": "Roxsy",
    "cachi": "Cachi",
}

# Number of consecutive offline scans before declaring departure (~15 min)
DEPARTURE_SCANS = 3


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_monitor_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitor_state (
            device_id INTEGER PRIMARY KEY REFERENCES devices(id),
            status TEXT NOT NULL DEFAULT 'unknown',
            changed_at TEXT,
            notified_at TEXT,
            dns_notified_at TEXT
        )
    """)
    conn.commit()


def send_telegram(message):
    token = CONFIG["telegram_bot_token"]
    chat_id = CONFIG["telegram_chat_id"]
    if not token or not chat_id:
        print(f"[SKIP] No Telegram credentials: {message}")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        print(f"[SENT] {message}")
        return True
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")
        return False


def is_in_cooldown(timestamp_str, cooldown_seconds):
    if not timestamp_str:
        return False
    try:
        last = datetime.fromisoformat(timestamp_str)
        return (datetime.now() - last).total_seconds() < cooldown_seconds
    except Exception:
        return False


def get_friendly_name(device_name, owner):
    """Turn 'Celular-Roxsy' into 'Roxsy' for messages."""
    return OWNER_NAMES.get(owner, device_name)


def get_last_n_scans(conn, device_id, n=3):
    """Get last N WiFi scan results for a device, newest first."""
    rows = conn.execute("""
        SELECT detected, timestamp FROM scan_logs
        WHERE device_id = ? AND scan_type = 'wifi'
        ORDER BY timestamp DESC LIMIT ?
    """, (device_id, n)).fetchall()
    return rows


def check_presence_events(conn):
    """Check for arrival/departure events."""
    now = datetime.now().isoformat()
    devices = conn.execute("""
        SELECT id, name, owner FROM devices
        WHERE name IN ({})
    """.format(",".join("?" for _ in CONFIG["monitor_devices"])),
        CONFIG["monitor_devices"],
    ).fetchall()

    for dev in devices:
        scans = get_last_n_scans(conn, dev["id"], DEPARTURE_SCANS)
        if not scans:
            continue

        current_online = scans[0]["detected"] == 1

        # Get or create monitor state
        state = conn.execute(
            "SELECT * FROM monitor_state WHERE device_id = ?", (dev["id"],)
        ).fetchone()

        if not state:
            status = "online" if current_online else "offline"
            conn.execute(
                "INSERT INTO monitor_state (device_id, status, changed_at) VALUES (?, ?, ?)",
                (dev["id"], status, now),
            )
            conn.commit()
            continue

        prev_status = state["status"]
        friendly = get_friendly_name(dev["name"], dev["owner"])

        # ARRIVAL: was offline, now online
        if prev_status in ("offline", "unknown") and current_online:
            if CONFIG["events"]["arrival"] and not is_in_cooldown(
                state["notified_at"], CONFIG["cooldowns"]["arrival"]
            ):
                send_telegram(
                    f"🏠 {friendly} llegó a casa ({dev['name']} conectado)"
                )
                conn.execute(
                    "UPDATE monitor_state SET status='online', changed_at=?, notified_at=? WHERE device_id=?",
                    (now, now, dev["id"]),
                )
            else:
                conn.execute(
                    "UPDATE monitor_state SET status='online', changed_at=? WHERE device_id=?",
                    (now, dev["id"]),
                )
            conn.commit()

        # DEPARTURE: was online, last N scans all offline
        elif prev_status == "online" and len(scans) >= DEPARTURE_SCANS:
            all_offline = all(s["detected"] == 0 for s in scans)
            if all_offline:
                if CONFIG["events"]["departure"] and not is_in_cooldown(
                    state["notified_at"], CONFIG["cooldowns"]["departure"]
                ):
                    mins = DEPARTURE_SCANS * 5
                    send_telegram(
                        f"👋 {friendly} salió de casa (hace ~{mins}min)"
                    )
                    conn.execute(
                        "UPDATE monitor_state SET status='offline', changed_at=?, notified_at=? WHERE device_id=?",
                        (now, now, dev["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE monitor_state SET status='offline', changed_at=? WHERE device_id=?",
                        (now, dev["id"]),
                    )
                conn.commit()


def check_dns_blocked(conn):
    """Check AdGuard query log for blocked DNS queries."""
    categories = CONFIG["events"]["dns_categories"]
    if not categories:
        return

    try:
        url = f"{ADGUARD_URL}/control/querylog?limit=100"
        credentials = base64.b64encode(
            f"{ADGUARD_USER}:{ADGUARD_PASS}".encode()
        ).decode()
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {credentials}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[ERROR] AdGuard query failed: {e}")
        return

    # Build IP->device mapping
    devices = conn.execute(
        "SELECT id, name, owner, wifi_ip FROM devices WHERE wifi_ip IS NOT NULL"
    ).fetchall()
    ip_to_dev = {d["wifi_ip"]: dict(d) for d in devices}

    now = datetime.now()
    cutoff = (now - timedelta(minutes=6)).isoformat()

    for entry in data.get("data", []):
        reason = entry.get("reason", "")
        if reason not in categories:
            continue

        client_ip = entry.get("client", "")
        dev = ip_to_dev.get(client_ip)
        if not dev:
            continue

        # Only process recent entries
        entry_time = entry.get("time", "")
        if entry_time and entry_time < cutoff:
            continue

        domain = entry.get("question", {}).get("name", "unknown")

        # Check cooldown per device
        state = conn.execute(
            "SELECT dns_notified_at FROM monitor_state WHERE device_id = ?",
            (dev["id"],),
        ).fetchone()

        if state and is_in_cooldown(
            state["dns_notified_at"], CONFIG["cooldowns"]["dns"]
        ):
            continue

        # Map reason to readable label
        reason_label = {
            "FilteredSafeBrowsing": "seguridad",
            "FilteredParental": "parental",
            "FilteredBlockedService": "servicio bloqueado",
        }.get(reason, reason)

        friendly = get_friendly_name(dev["name"], dev["owner"])
        send_telegram(
            f"🚫 {dev['name']} intentó acceder a sitio bloqueado: "
            f"<b>{domain}</b> ({reason_label})"
        )

        now_str = now.isoformat()
        conn.execute("""
            INSERT INTO monitor_state (device_id, status, dns_notified_at)
            VALUES (?, 'unknown', ?)
            ON CONFLICT(device_id) DO UPDATE SET dns_notified_at = ?
        """, (dev["id"], now_str, now_str))
        conn.commit()


def check_idle_devices(conn):
    """Check for online devices with no DNS activity in the last hour."""
    idle_minutes = CONFIG["events"]["idle_minutes"]
    if not idle_minutes:
        return

    devices = conn.execute("""
        SELECT d.id, d.name, d.owner, d.wifi_ip, ms.status, ms.notified_at
        FROM devices d
        JOIN monitor_state ms ON ms.device_id = d.id
        WHERE ms.status = 'online' AND d.name IN ({})
    """.format(",".join("?" for _ in CONFIG["monitor_devices"])),
        CONFIG["monitor_devices"],
    ).fetchall()

    if not devices:
        return

    # Get DNS activity from AdGuard
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
    except Exception as e:
        print(f"[ERROR] AdGuard query for idle check failed: {e}")
        return

    cutoff = (datetime.now() - timedelta(minutes=idle_minutes)).isoformat()

    # Count queries per IP in the last hour
    ip_query_count = {}
    for entry in data.get("data", []):
        entry_time = entry.get("time", "")
        if entry_time and entry_time >= cutoff:
            client = entry.get("client", "")
            ip_query_count[client] = ip_query_count.get(client, 0) + 1

    now_str = datetime.now().isoformat()
    for dev in devices:
        queries = ip_query_count.get(dev["wifi_ip"], 0)
        if queries > 0:
            continue

        if is_in_cooldown(dev["notified_at"], CONFIG["cooldowns"]["idle"]):
            continue

        friendly = get_friendly_name(dev["name"], dev["owner"])
        send_telegram(
            f"💤 {friendly} sin actividad hace {idle_minutes}min (descansando?)"
        )
        conn.execute(
            "UPDATE monitor_state SET notified_at = ? WHERE device_id = ?",
            (now_str, dev["id"]),
        )
        conn.commit()


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        return

    conn = get_db()
    init_monitor_table(conn)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitor check started")

    check_presence_events(conn)
    check_dns_blocked(conn)
    check_idle_devices(conn)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitor check done")
    conn.close()


if __name__ == "__main__":
    main()
