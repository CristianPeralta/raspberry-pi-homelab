#!/usr/bin/env python3
"""reaction-collector.py — Capture Telegram emoji reactions and map to CSAT scores.

Runs via cron (*/10) to collect reactions from both bot tokens.
If polling conflicts with the bot frameworks, the user falls back to benchmark-cli.py interactive.

Emoji → CSAT mapping:
  👎=1, 😕=2, 👍=3, 🔥=4, 🏆=5
"""

import json
import os
import sqlite3
import urllib.request
import urllib.error

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark.db")

# Bot tokens from environment
OC_TOKEN = os.environ.get("BENCHMARK_OC_BOT_TOKEN", "")
NB_TOKEN = os.environ.get("BENCHMARK_NB_BOT_TOKEN", "")

EMOJI_TO_CSAT = {
    "\U0001f44e": 1,  # 👎
    "\U0001f615": 2,  # 😕
    "\U0001f44d": 3,  # 👍
    "\U0001f525": 4,  # 🔥
    "\U0001f3c6": 5,  # 🏆
}

BOTS = [
    ("openclaw", OC_TOKEN),
    ("nanobot", NB_TOKEN),
]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def fetch_reactions(token):
    """Fetch message_reaction updates from Telegram Bot API (non-blocking)."""
    if not token:
        return []
    url = (
        f"https://api.telegram.org/bot{token}/getUpdates"
        f"?allowed_updates=[\"message_reaction\"]&timeout=0"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("result", [])
    except Exception as e:
        print(f"[ERROR] getUpdates failed: {e}")
        return []


def process_reactions(bot_name, updates, conn):
    """Process reaction updates and insert into DB."""
    count = 0
    for update in updates:
        reaction = update.get("message_reaction")
        if not reaction:
            continue

        chat_id = reaction.get("chat", {}).get("id")
        message_id = reaction.get("message_id")
        new_reactions = reaction.get("new_reaction", [])

        for r in new_reactions:
            emoji = r.get("emoji", "")
            csat = EMOJI_TO_CSAT.get(emoji)
            if csat is None:
                continue

            # Check if already recorded
            existing = conn.execute(
                "SELECT id FROM reactions WHERE bot=? AND chat_id=? AND message_id=?",
                (bot_name, chat_id, message_id),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO reactions (message_id, chat_id, bot, emoji, csat_score) VALUES (?,?,?,?,?)",
                (message_id, chat_id, bot_name, emoji, csat),
            )

            # Try to update queries table via telegram_messages mapping
            tm = conn.execute(
                "SELECT query_id FROM telegram_messages WHERE bot=? AND chat_id=? AND message_id=?",
                (bot_name, chat_id, message_id),
            ).fetchone()
            if tm:
                col = "csat_oc" if bot_name == "openclaw" else "csat_nb"
                conn.execute(
                    f"UPDATE queries SET {col} = ? WHERE id = ?",
                    (csat, tm["query_id"]),
                )

            count += 1

    if count:
        conn.commit()
        print(f"[{bot_name}] {count} new reactions recorded")


def main():
    if not os.path.exists(DB_PATH):
        print("[ERROR] benchmark.db not found. Run init-db.py first.")
        return

    conn = get_db()
    for bot_name, token in BOTS:
        if not token:
            print(f"[SKIP] {bot_name}: no token configured")
            continue
        updates = fetch_reactions(token)
        if updates:
            process_reactions(bot_name, updates, conn)
        else:
            print(f"[{bot_name}] no reactions")
    conn.close()


if __name__ == "__main__":
    main()
