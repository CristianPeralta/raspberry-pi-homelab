"""Housing Hunter — Scraper de periodicos locales y clasificados via Google.

Fuentes:
- Correo (edicion regional): scrape HTML de la seccion local.
- Google Search: busca clasificados publicados en redes/web de periodicos locales.

Las URLs y queries se construyen desde config.yaml (ciudad, periodicos).
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from config import (
    HEADERS, CIUDAD, PERIODICOS, ALQUILER_MAX_PEN, VENTA_MAX_USD,
    get_db, insert_property, guess_distrito as _guess_distrito_cfg,
)

log = logging.getLogger("housing.periodicos")


def fetch(url, timeout=15):
    """Fetch a URL and return BeautifulSoup, or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


def extract_price(text):
    """Extract numeric price from text."""
    if not text:
        return None, None
    text = text.replace(",", "")
    m = re.search(r"(?:US?\$|USD)\s*([\d.]+)", text)
    if m:
        return float(m.group(1).rstrip(".")), "USD"
    m = re.search(r"(?:S/?\.?\s*)([\d.]+)", text)
    if m:
        return float(m.group(1).rstrip(".")), "PEN"
    return None, None


def is_housing_related(text):
    """Check if text is related to housing/real estate."""
    keywords = [
        "alquil", "renta", "arriendo", "venta", "vendo",
        "terreno", "lote", "casa", "departamento", "depa",
        "habitacion", "cuarto", "minidepartamento",
        "inmueble", "propiedad",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


def classify_modo(text):
    """Classify if the listing is for rent or sale."""
    t = text.lower()
    if any(w in t for w in ["alquil", "renta", "arriendo"]):
        return "alquiler"
    if any(w in t for w in ["vent", "vendo", "remato"]):
        return "venta"
    return "alquiler"


def guess_tipo(text):
    """Guess property type."""
    t = text.lower()
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "casa" in t:
        return "casa"
    if "depa" in t or "departamento" in t:
        return "departamento"
    return "otro"


def guess_distrito(text):
    return _guess_distrito_cfg(text)


# --- CORREO (edicion regional) ---

def scrape_correo():
    """Scrape Correo regional edition for real estate related articles."""
    correo_cfg = PERIODICOS.get("correo", {})
    url = correo_cfg.get("web")
    if not url:
        log.info("Correo: no URL configured, skipping")
        return []

    results = []
    soup = fetch(url)
    if not soup:
        return results

    base_domain = url.split("/edicion")[0] if "/edicion" in url else url.rstrip("/")

    articles = soup.select("article, [class*=story], [class*=nota], [class*=card]")
    for article in articles:
        title_el = article.select_one("h2, h3, h4, a")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        body = article.get_text(strip=True)

        if not is_housing_related(title) and not is_housing_related(body):
            continue

        # Filter out news articles — real classifieds have price or contact info
        has_price = bool(extract_price(body)[0])
        has_contact = bool(re.search(
            r"\d{9}|\d{3}[\s-]\d{3}[\s-]\d{3}|whatsapp|contactar|llamar|cel",
            body.lower(),
        ))
        if not has_price and not has_contact:
            continue

        link_el = article.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = base_domain + href

        precio, moneda = extract_price(body)
        modo = classify_modo(body)

        results.append({
            "modo": modo,
            "tipo": guess_tipo(body),
            "titulo": f"Correo: {title[:180]}",
            "precio": precio or 0,
            "moneda": moneda or "PEN",
            "fuente": "periodico",
            "fuente_detalle": "Correo",
            "url": href,
            "distrito": guess_distrito(body),
        })

    return results


# --- GOOGLE SEARCH: clasificados ---

def scrape_google_clasificados():
    """Search Google for recent classified ads from local newspapers."""
    results = []
    ciudad = CIUDAD

    queries = [
        # Alquiler
        f'"{ciudad}" alquiler casa departamento -inmobiliaria site:facebook.com',
        f'"{ciudad}" alquiler cuarto habitacion',
        # Venta
        f'"{ciudad}" venta terreno lote -inmobiliaria',
        f'"{ciudad}" "se vende" terreno casa',
    ]

    # Add newspaper-specific queries
    for paper_name in PERIODICOS:
        clean_name = paper_name.replace("_", " ")
        queries.append(f'"{clean_name}" {ciudad} alquiler OR venta OR terreno')

    for query in queries:
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10&hl=es&tbs=qdr:w"
        try:
            resp = requests.get(search_url, headers={
                **HEADERS,
                "Accept": "text/html,application/xhtml+xml",
            }, timeout=15)
            if resp.status_code != 200:
                log.warning(f"Google returned {resp.status_code} for query: {query[:50]}")
                continue
        except Exception as e:
            log.error(f"Google search failed: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select("div.g, div[data-hveid]"):
            title_el = result.select_one("h3")
            link_el = result.select_one("a[href]")
            snippet_el = result.select_one(".VwiC3b, .st, [data-sncf]")

            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            href = link_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            full_text = f"{title} {snippet}"

            if not is_housing_related(full_text):
                continue

            precio, moneda = extract_price(full_text)
            modo = classify_modo(full_text)

            # Determine source
            fuente_detalle = "Google Clasificados"
            if "facebook.com" in href:
                fuente_detalle = "Facebook (via Google)"
            for paper_name in PERIODICOS:
                if paper_name.replace("_", " ") in full_text.lower():
                    fuente_detalle = f"{paper_name} (via Google)"
                    break

            results.append({
                "modo": modo,
                "tipo": guess_tipo(full_text),
                "titulo": title[:200],
                "precio": precio or 0,
                "moneda": moneda or "PEN",
                "fuente": "periodico",
                "fuente_detalle": fuente_detalle,
                "url": href,
                "distrito": guess_distrito(full_text),
                "notas": snippet[:300] if snippet else None,
            })

    return results


# --- MAIN ---

def scrape_all_periodicos():
    """Run all newspaper/classified scrapers and insert results into DB."""
    conn = get_db()
    total_new = 0

    scrapers = [
        ("Correo", scrape_correo),
        ("Google Clasificados", scrape_google_clasificados),
    ]

    for name, scraper_fn in scrapers:
        log.info(f"Scraping: {name}")
        try:
            results = scraper_fn()
            new_count = 0
            for prop in results:
                prop_id = insert_property(conn, prop)
                if prop_id:
                    new_count += 1
            total_new += new_count
            log.info(f"  {name}: {len(results)} found, {new_count} new")

            conn.execute(
                "INSERT INTO busquedas (fuente, modo, propiedades_encontradas, propiedades_nuevas) "
                "VALUES (?, ?, ?, ?)",
                (name, "ambos", len(results), new_count),
            )
            conn.commit()
        except Exception as e:
            log.error(f"  {name} failed: {e}")

    conn.close()
    return total_new


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    total = scrape_all_periodicos()
    print(f"Total new from newspapers/classifieds: {total}")
