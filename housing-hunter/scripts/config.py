"""Housing Hunter — Shared configuration.

Reads personal preferences from config.yaml (gitignored).
Reads secrets from .env (gitignored).
"""

import os
import sqlite3
from pathlib import Path

try:
    import yaml
except ImportError:
    # Inline minimal YAML parser for simple key-value configs
    import json
    yaml = None

# Paths
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
DB_PATH = BASE_DIR / "db" / "housing.db"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Load .env file if it exists (for cron and manual runs)
_env_file = SCRIPT_DIR / ".env"
if _env_file.exists():
    for line in _env_file.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ============================================================
# Load config.yaml
# ============================================================

def _load_yaml(path):
    """Load YAML config file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found: {path}\n"
            f"Copy config.yaml.example to config.yaml and fill in your values."
        )
    if yaml:
        with open(path) as f:
            return yaml.safe_load(f)
    else:
        # Fallback: try json (won't work for YAML but gives clear error)
        raise ImportError("PyYAML required: pip install pyyaml")


_cfg = _load_yaml(SCRIPT_DIR / "config.yaml")

# Search params
_search = _cfg.get("search", {})
CIUDAD = _search.get("ciudad", "")

SEARCH_CONFIG = {
    "alquiler": {
        "ciudad": CIUDAD,
        "precio_max": _search.get("alquiler", {}).get("precio_max_pen", 1000),
        "tipos": _search.get("alquiler", {}).get("tipos", []),
        "requisitos": _search.get("alquiler", {}).get("requisitos", []),
    },
    "venta": {
        "ciudad": CIUDAD,
        "precio_min_usd": _search.get("venta", {}).get("precio_min_usd", 0),
        "precio_max_usd": _search.get("venta", {}).get("precio_max_usd", 50000),
        "tipos": _search.get("venta", {}).get("tipos", []),
    },
}

ALQUILER_MAX_PEN = SEARCH_CONFIG["alquiler"]["precio_max"]
VENTA_MAX_USD = SEARCH_CONFIG["venta"]["precio_max_usd"]

# Districts
DISTRITOS = _cfg.get("distritos", [])

# District aliases for guessing from text
DISTRITO_ALIASES = _cfg.get("distrito_aliases", {})

# Canonical district map (lowercase key -> display name)
DISTRITO_MAP = {}
for d in DISTRITOS:
    DISTRITO_MAP[d.lower()] = d.title()
for alias, canonical in DISTRITO_ALIASES.items():
    DISTRITO_MAP[alias.lower()] = canonical

# User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-PE,es;q=0.9",
}

# Portal URLs — build flat list of (portal_name, url, modo)
def _build_portal_list(key):
    """Build list of (name, url, modo) from config portales section."""
    result = []
    section = _cfg.get(key, {})
    for portal_name, entries in section.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            result.append((portal_name, entry["url"], entry["modo"]))
    return result

PORTAL_URLS = _build_portal_list("portales")
PORTAL_PE_URLS = _build_portal_list("portales_pe")

# Facebook groups
FB_GROUPS = {}
for g in _cfg.get("facebook_groups", []):
    FB_GROUPS[str(g["id"])] = {
        "name": g["name"],
        "modo": g["modo"],
    }

# Newspapers
PERIODICOS = _cfg.get("periodicos", {})

# Dashboard settings
_dashboard = _cfg.get("dashboard", {})
DASHBOARD_PRESUPUESTO_ALQUILER = _dashboard.get("presupuesto_alquiler", "")
DASHBOARD_PRESUPUESTO_COMPRA = _dashboard.get("presupuesto_compra", "")
DASHBOARD_FECHA_INICIO = _dashboard.get("fecha_inicio", "")


# ============================================================
# DB helpers
# ============================================================

def get_db():
    """Return a sqlite3 connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def property_exists(conn, titulo, fuente):
    """Check if a property already exists in the DB."""
    row = conn.execute(
        "SELECT id FROM propiedades WHERE titulo = ? AND fuente_detalle = ?",
        (titulo, fuente),
    ).fetchone()
    return row is not None


def insert_property(conn, data):
    """Insert a new property and return its id, or None if duplicate."""
    if property_exists(conn, data.get("titulo", ""), data.get("fuente_detalle", "")):
        return None

    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cur = conn.execute(
        f"INSERT INTO propiedades ({cols}) VALUES ({placeholders})",
        list(data.values()),
    )
    conn.commit()
    return cur.lastrowid


def guess_distrito(text):
    """Guess district from text using configured aliases."""
    t = text.lower()
    for key, val in DISTRITO_MAP.items():
        if key in t:
            return val
    return CIUDAD.title() if CIUDAD else "Desconocido"
