"""Housing Hunter — Telegram notifications."""

import json
import urllib.request
import urllib.error
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CIUDAD, get_db

log = logging.getLogger("housing.notify")

# Telegram message limit
MAX_MSG_LEN = 4000


def send_telegram(message, parse_mode="HTML"):
    """Send a message via Telegram bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram credentials not set (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Split long messages
    chunks = [message[i:i+MAX_MSG_LEN] for i in range(0, len(message), MAX_MSG_LEN)]

    for chunk in chunks:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return False
        except urllib.error.URLError as e:
            log.error(f"Telegram send failed: {e}")
            return False

    return True


def _safe(val, default="--"):
    """Return val or default if None/empty."""
    if val is None or val == "" or val == 0:
        return default
    return val


def format_alquiler(row):
    """Format a rental property for Telegram."""
    precio = row.get("precio")
    if precio and precio > 0:
        precio_str = f"S/ {precio:,.0f}/mes"
    else:
        precio_str = "Precio por confirmar"

    parts = []
    area = row.get("area_m2")
    if area and area > 0:
        parts.append(f"{area:.0f}m2")
    hab = row.get("habitaciones")
    if hab and hab > 0:
        parts.append(f"{hab}hab")
    if row.get("tiene_patio"):
        parts.append("PATIO")
    mascotas = row.get("acepta_mascotas", "desconocido")
    if mascotas == "si":
        parts.append("MASCOTAS OK")
    elif mascotas == "negociable":
        parts.append("MASCOTAS?")

    detalles = " | ".join(parts) if parts else ""

    distrito = row.get("distrito") or CIUDAD.title()
    fuente = row.get("fuente_detalle") or "?"
    score = row.get("score")
    score_str = f"{score}%" if score else ""

    url_str = ""
    url = row.get("url")
    if url and url.startswith("http"):
        url_str = f'\n<a href="{url}">Ver anuncio</a>'

    line2_parts = [precio_str]
    if detalles:
        line2_parts.append(detalles)
    line2 = " | ".join(line2_parts)

    line3_parts = [distrito, fuente]
    if score_str:
        line3_parts.append(score_str)
    line3 = " | ".join(line3_parts)

    return f"<b>{row['titulo'][:80]}</b>\n{line2}\n{line3}{url_str}"


def format_venta(row):
    """Format a sale property for Telegram."""
    precio = row.get("precio")
    moneda = row.get("moneda", "USD")
    if precio and precio > 0:
        if moneda == "USD":
            precio_str = f"${precio:,.0f} USD"
        else:
            precio_str = f"S/ {precio:,.0f}"
    else:
        precio_str = "Precio por confirmar"

    parts = []
    area = row.get("area_m2")
    if area and area > 0:
        parts.append(f"{area:.0f}m2")
    titulo_s = row.get("titulo_saneado")
    if titulo_s and titulo_s not in ("desconocido", "por verificar"):
        parts.append(f"Titulo: {titulo_s}")

    detalles = " | ".join(parts) if parts else ""

    distrito = row.get("distrito") or CIUDAD.title()
    fuente = row.get("fuente_detalle") or "?"
    score = row.get("score")
    score_str = f"{score}%" if score else ""

    url_str = ""
    url = row.get("url")
    if url and url.startswith("http"):
        url_str = f'\n<a href="{url}">Ver anuncio</a>'

    line2_parts = [precio_str]
    if detalles:
        line2_parts.append(detalles)
    line2 = " | ".join(line2_parts)

    line3_parts = [distrito, fuente]
    if score_str:
        line3_parts.append(score_str)
    line3 = " | ".join(line3_parts)

    return f"<b>{row['titulo'][:80]}</b>\n{line2}\n{line3}{url_str}"


def notify_new_properties():
    """Check for new properties and send Telegram alerts."""
    conn = get_db()

    nuevas_alquiler = conn.execute(
        "SELECT * FROM propiedades WHERE modo='alquiler' AND estado='nueva' "
        "AND fecha_encontrada = date('now') AND notificado = 0"
    ).fetchall()

    nuevas_venta = conn.execute(
        "SELECT * FROM propiedades WHERE modo='venta' AND estado='nueva' "
        "AND fecha_encontrada = date('now') AND notificado = 0"
    ).fetchall()

    if not nuevas_alquiler and not nuevas_venta:
        log.info("No new properties to notify")
        return 0

    sent = 0

    if nuevas_alquiler:
        msg = f"<b>ALQUILER — {len(nuevas_alquiler)} nueva(s)</b>\n\n"
        for row in nuevas_alquiler:
            msg += format_alquiler(dict(row)) + "\n\n"
        if send_telegram(msg.strip()):
            for row in nuevas_alquiler:
                conn.execute("UPDATE propiedades SET notificado=1 WHERE id=?", (row["id"],))
            sent += len(nuevas_alquiler)

    if nuevas_venta:
        msg = f"<b>VENTA — {len(nuevas_venta)} nueva(s)</b>\n\n"
        for row in nuevas_venta:
            msg += format_venta(dict(row)) + "\n\n"
        if send_telegram(msg.strip()):
            for row in nuevas_venta:
                conn.execute("UPDATE propiedades SET notificado=1 WHERE id=?", (row["id"],))
            sent += len(nuevas_venta)

    conn.commit()
    conn.close()
    log.info(f"Notified {sent} new properties via Telegram")
    return sent


def send_daily_summary():
    """Send a daily summary of active searches."""
    conn = get_db()

    total_alquiler = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE modo='alquiler' AND estado NOT IN ('descartada','cerrada')"
    ).fetchone()[0]
    total_venta = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE modo='venta' AND estado NOT IN ('descartada','cerrada')"
    ).fetchone()[0]
    nuevas_hoy = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE fecha_encontrada = date('now')"
    ).fetchone()[0]
    descartadas = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE estado='descartada'"
    ).fetchone()[0]
    contactadas = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE estado='contactada'"
    ).fetchone()[0]

    top = conn.execute(
        "SELECT titulo, precio, moneda, score FROM propiedades "
        "WHERE modo='alquiler' AND estado NOT IN ('descartada','cerrada') "
        "AND precio > 0 ORDER BY score DESC LIMIT 3"
    ).fetchall()

    msg = (
        f"<b>HOUSING DAILY</b>\n\n"
        f"Nuevas hoy: {nuevas_hoy}\n"
        f"Alquileres activos: {total_alquiler}\n"
        f"Ventas activas: {total_venta}\n"
        f"Contactadas: {contactadas}\n"
        f"Descartadas: {descartadas}\n\n"
    )

    if top:
        msg += "<b>Top alquiler:</b>\n"
        for r in top:
            sym = "S/" if r["moneda"] == "PEN" else "$"
            precio = r["precio"]
            score = r["score"]
            score_str = f" ({score}%)" if score else ""
            msg += f"  {r['titulo'][:50]} — {sym}{precio:,.0f}{score_str}\n"

    conn.close()
    return send_telegram(msg.strip())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = notify_new_properties()
    print(f"Notified: {count}")
