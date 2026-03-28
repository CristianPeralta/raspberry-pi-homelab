#!/usr/bin/env python3
"""Initialize benchmark.db with schema for OpenClaw vs nanobot comparison."""

import os
import sqlite3

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "benchmark.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            query_text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'simple',

            oc_response TEXT,
            oc_time_ms INTEGER,
            oc_tokens_in INTEGER,
            oc_tokens_out INTEGER,
            oc_model TEXT,
            oc_tools_used TEXT,
            oc_error INTEGER DEFAULT 0,

            nb_response TEXT,
            nb_time_ms INTEGER,
            nb_tokens_in INTEGER,
            nb_tokens_out INTEGER,
            nb_model TEXT,
            nb_tools_used TEXT,
            nb_error INTEGER DEFAULT 0,

            csat_oc INTEGER CHECK(csat_oc BETWEEN 1 AND 5),
            csat_nb INTEGER CHECK(csat_nb BETWEEN 1 AND 5),

            notes TEXT,
            winner TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_queries_category ON queries(category);
        CREATE INDEX IF NOT EXISTS idx_queries_date ON queries(timestamp);

        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY,
            query_id INTEGER REFERENCES queries(id),
            bot TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(bot, chat_id, message_id)
        );

        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            bot TEXT NOT NULL,
            emoji TEXT NOT NULL,
            csat_score INTEGER CHECK(csat_score BETWEEN 1 AND 5),
            timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()
    print(f"benchmark.db initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
