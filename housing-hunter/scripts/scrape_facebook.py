"""Housing Hunter — Scraper de grupos de Facebook.

Usa facebook-scraper (pip install facebook-scraper) para monitorear
grupos públicos de alquiler y venta de propiedades.

Nota: solo funciona con grupos públicos sin login.
Si un grupo es privado, se necesita cookies/login (mayor riesgo de ban).
"""

import re
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    get_db, insert_property, guess_distrito as _guess_distrito_cfg,
    FB_GROUPS, ALQUILER_MAX_PEN, VENTA_MAX_USD,
)

log = logging.getLogger("housing.facebook")

# Optional: path to Facebook cookies file (Netscape format)
# Export from browser using "Get cookies.txt" extension
# Without cookies, most groups return 0 results (private or login wall)
COOKIES_FILE = Path(__file__).parent / "fb_cookies.txt"

# Keywords para clasificar posts
ALQUILER_KEYWORDS = [
    "alquil", "arriendo", "renta", "se alquila", "en alquiler",
]
VENTA_KEYWORDS = [
    "vend", "en venta", "se vende", "remato", "remate", "ocasion",
    "terreno", "lote",
]
SKIP_KEYWORDS = [
    "busco", "necesito", "buscando",  # demanda, no oferta
]


def extract_price(text):
    """Extract price and currency from Facebook post text."""
    if not text:
        return None, None
    text = text.replace(",", "").replace(".", "")
    # USD patterns
    m = re.search(r"(?:US?\$|USD|dolares?)\s*(\d+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), "USD"
    # Soles patterns
    m = re.search(r"(?:S/?\.?\s*)(\d+)", text)
    if m:
        val = float(m.group(1))
        if val >= 50:  # ignore tiny numbers
            return val, "PEN"
    # Plain number near "soles"
    m = re.search(r"(\d+)\s*soles", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), "PEN"
    return None, None


def extract_phone(text):
    """Extract phone number from post text."""
    if not text:
        return None
    m = re.search(r"(?:9\d{8})", text)
    if m:
        return m.group(0)
    m = re.search(r"(?:(?:\+?51)?[\s-]?)?(\d{3}[\s-]?\d{3}[\s-]?\d{3})", text)
    if m:
        return m.group(0).replace(" ", "").replace("-", "")
    return None


def guess_tipo(text):
    """Guess property type from post text."""
    t = text.lower()
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "casa" in t:
        return "casa"
    if "depa" in t or "departamento" in t:
        return "departamento"
    if "habitacion" in t or "cuarto" in t or "minidepa" in t:
        return "habitacion"
    return "otro"


def guess_distrito(text):
    """Guess district from post text using config aliases."""
    return _guess_distrito_cfg(text)


def extract_area(text):
    """Extract area in m2."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]?", text)
    return float(m.group(1)) if m else None


def extract_rooms(text):
    """Extract room count."""
    if not text:
        return None
    m = re.search(r"(\d+)\s*(?:hab|dorm|cuarto|recamara)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def classify_modo(text, default_modo):
    """Classify post as alquiler or venta based on text."""
    t = text.lower()

    # Skip demand posts
    for kw in SKIP_KEYWORDS:
        if t.startswith(kw) or t[:30].find(kw) >= 0:
            return None

    if default_modo != "ambos":
        return default_modo

    alq_score = sum(1 for kw in ALQUILER_KEYWORDS if kw in t)
    ven_score = sum(1 for kw in VENTA_KEYWORDS if kw in t)

    if alq_score > ven_score:
        return "alquiler"
    if ven_score > alq_score:
        return "venta"
    return "venta"  # default for ambiguous posts in mixed groups


def filter_budget(modo, precio, moneda):
    """Return True if property is within budget."""
    if precio is None or precio == 0:
        return True
    if modo == "alquiler" and moneda == "PEN" and precio > ALQUILER_MAX_PEN:
        return False
    if modo == "venta" and moneda == "USD" and precio > VENTA_MAX_USD:
        return False
    if modo == "venta" and moneda == "PEN" and precio > VENTA_MAX_USD * 4:
        return False
    return True


def is_property_post(text):
    """Check if post looks like a property listing (not just chat/memes)."""
    if not text or len(text) < 20:
        return False
    t = text.lower()
    property_words = [
        "alquil", "vend", "renta", "arriendo", "terreno", "lote",
        "casa", "departamento", "depa", "habitacion", "cuarto",
        "minidepa", "local", "cochera",
    ]
    return any(w in t for w in property_words)


def scrape_fb_group(group_id, group_info, max_pages=3):
    """Scrape a single Facebook group for property posts."""
    try:
        from facebook_scraper import get_posts
    except ImportError:
        log.error("facebook-scraper not installed: pip install facebook-scraper lxml_html_clean")
        return []

    group_name = group_info["name"]
    default_modo = group_info["modo"]
    results = []

    # Only get posts from last 7 days
    cutoff = datetime.now() - timedelta(days=7)

    try:
        kwargs = {
            "group": group_id,
            "pages": max_pages,
            "timeout": 20,
            "options": {"allow_extra_requests": False},
        }
        # Use cookies if available (required for private groups / login wall)
        if COOKIES_FILE.exists():
            kwargs["cookies"] = str(COOKIES_FILE)
            log.debug(f"Using cookies from {COOKIES_FILE}")

        posts = get_posts(**kwargs)

        for post in posts:
            text = post.get("text") or post.get("post_text") or ""
            if not is_property_post(text):
                continue

            # Check post date
            post_time = post.get("time")
            if post_time and post_time < cutoff:
                continue

            modo = classify_modo(text, default_modo)
            if modo is None:  # skip demand posts
                continue

            precio, moneda = extract_price(text)
            if not filter_budget(modo, precio, moneda):
                continue

            # Build title from first line or first 80 chars
            title_line = text.split("\n")[0][:100].strip()
            if len(title_line) < 10:
                title_line = text[:100].strip()

            phone = extract_phone(text)
            post_url = post.get("post_url") or ""

            results.append({
                "modo": modo,
                "tipo": guess_tipo(text),
                "titulo": title_line[:200],
                "precio": precio or 0,
                "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
                "area_m2": extract_area(text),
                "habitaciones": extract_rooms(text),
                "distrito": guess_distrito(text),
                "fuente": "facebook",
                "fuente_detalle": f"FB:{group_name[:40]}",
                "url": post_url,
                "contacto_telefono": phone,
                "destacado": text[:300] if len(text) > 100 else None,
            })

    except Exception as e:
        log.error(f"  FB group {group_id} ({group_name}): {e}")

    return results


def scrape_all_facebook():
    """Run Facebook group scrapers and insert results into DB."""
    conn = get_db()
    total_new = 0

    for group_id, group_info in FB_GROUPS.items():
        name = group_info["name"]
        log.info(f"Scraping FB: {name}")

        results = scrape_fb_group(group_id, group_info)
        new_count = 0
        for prop in results:
            prop_id = insert_property(conn, prop)
            if prop_id:
                new_count += 1
        total_new += new_count
        log.info(f"  FB {name[:30]}: {len(results)} found, {new_count} new")

        conn.execute(
            "INSERT INTO busquedas (fuente, modo, propiedades_encontradas, propiedades_nuevas) "
            "VALUES (?, ?, ?, ?)",
            (f"FB:{name[:40]}", group_info["modo"], len(results), new_count),
        )
        conn.commit()

    conn.close()
    return total_new


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    total = scrape_all_facebook()
    print(f"Total new from Facebook: {total}")
