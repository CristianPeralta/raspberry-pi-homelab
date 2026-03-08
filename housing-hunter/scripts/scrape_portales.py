"""Housing Hunter — Scraper de portales inmobiliarios.

Nestoria: requests + BeautifulSoup (server-rendered HTML).
LaEncontre, Properati, Urbania: Playwright headless Chromium (JS-rendered).
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from config import HEADERS, PORTAL_URLS, ALQUILER_MAX_PEN, VENTA_MAX_USD, CIUDAD, get_db, insert_property
from config import guess_distrito as _guess_distrito_cfg

log = logging.getLogger("housing.portales")

# Lazy Playwright browser instance
_browser = None
_playwright = None


def get_browser():
    """Get or create a Playwright browser instance."""
    global _browser, _playwright
    if _browser is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
    return _browser


def close_browser():
    """Close the Playwright browser."""
    global _browser, _playwright
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None


def fetch_html(url, timeout=15):
    """Fetch URL with requests, return BeautifulSoup."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.error(f"fetch_html failed {url}: {e}")
        return None


def fetch_js(url, wait_selector=None, timeout=30000):
    """Fetch URL with Playwright (JS rendering), return BeautifulSoup."""
    try:
        browser = get_browser()
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            locale="es-PE",
        )
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")

        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=10000)
            except Exception:
                log.debug(f"Selector {wait_selector} not found, using page as-is")

        # Extra wait for lazy-loaded content
        page.wait_for_timeout(3000)

        html = page.content()
        page.close()
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        log.error(f"fetch_js failed {url}: {e}")
        return None


def extract_price(text):
    """Extract numeric price from text like 'S/. 1,500' or 'US$ 27,000'."""
    if not text:
        return None, None
    text = text.strip()
    clean = text.replace(",", "")
    m = re.search(r"(?:US?\$|USD)\s*([\d.]+)", clean)
    if m:
        val = m.group(1).rstrip(".")
        return float(val), "USD"
    m = re.search(r"(?:S/?\.?\s*)([\d.]+)", clean)
    if m:
        val = m.group(1).rstrip(".")
        return float(val), "PEN"
    return None, None


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


def guess_tipo(title):
    """Guess property type from title."""
    t = title.lower()
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "casa" in t:
        return "casa"
    if "depa" in t or "departamento" in t:
        return "departamento"
    if "habitacion" in t or "cuarto" in t:
        return "habitacion"
    return "otro"


def guess_distrito(title):
    """Guess district from title using config aliases."""
    return _guess_distrito_cfg(title)


def filter_budget(modo, precio, moneda):
    """Return True if property is within budget."""
    if precio is None or precio == 0:
        return True  # keep unknowns for manual review
    if modo == "alquiler" and moneda == "PEN" and precio > ALQUILER_MAX_PEN:
        return False
    if modo == "venta" and moneda == "USD" and precio > VENTA_MAX_USD:
        return False
    if modo == "venta" and moneda == "PEN" and precio > VENTA_MAX_USD * 4:
        return False
    return True


# ============================================================
# NESTORIA — HTML directo (requests)
# ============================================================

def scrape_nestoria(url, modo):
    """Scrape Nestoria using server-rendered HTML."""
    soup = fetch_html(url)
    if not soup:
        return []

    results = []
    for item in soup.select(".listing_list"):
        title_el = item.select_one(".listing__title__text")
        price_el = item.select_one(".result__details__price")
        info_el = item.select_one(".listing_list__info")

        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            continue

        precio, moneda = extract_price(price_el.get_text() if price_el else "")
        area = extract_area(info_el.get_text() if info_el else "")
        rooms = extract_rooms(info_el.get_text() if info_el else "")

        if not filter_budget(modo, precio, moneda):
            continue

        link_el = item.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.nestoria.pe" + href

        results.append({
            "modo": modo,
            "tipo": guess_tipo(title),
            "titulo": title[:200],
            "precio": precio or 0,
            "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
            "area_m2": area,
            "habitaciones": rooms,
            "fuente": "clasificado",
            "fuente_detalle": "Nestoria",
            "url": href or url,
            "distrito": guess_distrito(title),
        })

    return results


# ============================================================
# LAENCONTRE — Playwright
# ============================================================

def scrape_laencontre(url, modo):
    """Scrape LaEncontre using Playwright for JS rendering."""
    soup = fetch_js(url, wait_selector=".ListingCell, [class*=listing], [class*=Card]")
    if not soup:
        return []

    results = []
    # LaEncontre uses various listing card selectors
    selectors = [
        ".ListingCell", "[class*=ListingCard]", "[class*=listing-card]",
        "[class*=propertyCard]", "[data-testid*=listing]",
        "article", ".aviso",
    ]
    listings = []
    for sel in selectors:
        listings = soup.select(sel)
        if len(listings) > 1:
            break

    if not listings:
        # Fallback: try to find any card-like structure with price info
        all_divs = soup.find_all("div", class_=True)
        for div in all_divs:
            classes = " ".join(div.get("class", []))
            if any(kw in classes.lower() for kw in ["card", "listing", "item", "property", "aviso"]):
                text = div.get_text()
                if re.search(r"S/|USD|\$|m²|m2", text):
                    listings.append(div)

    for item in listings:
        text = item.get_text(separator=" ", strip=True)
        if len(text) < 10:
            continue

        # Extract title (first heading or strong text)
        title_el = item.select_one("h2, h3, h4, a[class*=title], strong, [class*=title], [class*=address]")
        title = title_el.get_text(strip=True) if title_el else text[:100]

        # Skip UI elements
        if title.lower() in ("ordenar", "filtros", "ver mapa", "login"):
            continue

        precio, moneda = extract_price(text)
        area = extract_area(text)

        if not filter_budget(modo, precio, moneda):
            continue

        link_el = item.select_one("a[href*='/inmueble/'], a[href*='/propiedad/'], a[href*='/venta/'], a[href*='/alquiler/']")
        if not link_el:
            link_el = item.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.laencontre.com.pe" + href

        results.append({
            "modo": modo,
            "tipo": guess_tipo(text),
            "titulo": title[:200],
            "precio": precio or 0,
            "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
            "area_m2": area,
            "fuente": "clasificado",
            "fuente_detalle": "LaEncontre",
            "url": href or url,
            "distrito": guess_distrito(text),
        })

    return results


# ============================================================
# PROPERATI — Playwright
# ============================================================

def scrape_properati(url, modo):
    """Scrape Properati using Playwright."""
    soup = fetch_js(url, wait_selector="[class*=listing], [class*=card], [class*=Card]")
    if not soup:
        return []

    results = []
    selectors = [
        "[class*=ListingCard]", "[class*=listing-card]", "[class*=propertyCard]",
        "article[class*=listing]", "[data-qa=posting]", "[class*=CardContainer]",
    ]
    listings = []
    for sel in selectors:
        listings = soup.select(sel)
        if len(listings) > 1:
            break

    if not listings:
        all_divs = soup.find_all("div", class_=True)
        for div in all_divs:
            classes = " ".join(div.get("class", []))
            if any(kw in classes.lower() for kw in ["card", "listing", "result"]):
                text = div.get_text()
                if re.search(r"S/|USD|\$|m²|m2", text) and CIUDAD in text.lower():
                    listings.append(div)

    for item in listings:
        text = item.get_text(separator=" ", strip=True)
        if len(text) < 10:
            continue

        title_el = item.select_one("h2, h3, [class*=title], [class*=address], [class*=Title]")
        title = title_el.get_text(strip=True) if title_el else text[:100]

        if title.lower() in ("ordenar", "filtros", "ver mapa"):
            continue

        precio, moneda = extract_price(text)
        area = extract_area(text)

        if not filter_budget(modo, precio, moneda):
            continue

        link_el = item.select_one("a[href*='/detalle/'], a[href*='/inmueble/'], a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.properati.com.pe" + href

        results.append({
            "modo": modo,
            "tipo": guess_tipo(text),
            "titulo": title[:200],
            "precio": precio or 0,
            "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
            "area_m2": area,
            "fuente": "clasificado",
            "fuente_detalle": "Properati",
            "url": href or url,
            "distrito": guess_distrito(text),
        })

    return results


# ============================================================
# URBANIA — Playwright
# ============================================================

def scrape_urbania(url, modo):
    """Scrape Urbania using Playwright."""
    soup = fetch_js(url, wait_selector="[data-qa=posting], [class*=postingCard], [class*=CardContainer]")
    if not soup:
        return []

    results = []
    selectors = [
        "[data-qa=posting]", "[class*=postingCard]", "[class*=PostingCard]",
        "[class*=CardContainer]", "article",
    ]
    listings = []
    for sel in selectors:
        listings = soup.select(sel)
        if len(listings) > 1:
            break

    if not listings:
        all_divs = soup.find_all("div", class_=True)
        for div in all_divs:
            classes = " ".join(div.get("class", []))
            if any(kw in classes.lower() for kw in ["posting", "card", "listing"]):
                text = div.get_text()
                if re.search(r"S/|USD|\$|m²|m2", text):
                    listings.append(div)

    for item in listings:
        text = item.get_text(separator=" ", strip=True)
        if len(text) < 10:
            continue

        title_el = item.select_one("[data-qa=posting-title], h2, h3, [class*=title], [class*=Title]")
        title = title_el.get_text(strip=True) if title_el else text[:100]
        price_el = item.select_one("[data-qa=posting-price], [class*=price], [class*=Price]")
        price_text = price_el.get_text() if price_el else text

        if title.lower() in ("ordenar", "filtros", "ver mapa"):
            continue

        precio, moneda = extract_price(price_text)
        area = extract_area(text)

        if not filter_budget(modo, precio, moneda):
            continue

        link_el = item.select_one("a[href*='/propiedades/'], a[href*='/inmueble/'], a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://urbania.pe" + href

        results.append({
            "modo": modo,
            "tipo": guess_tipo(text),
            "titulo": title[:200],
            "precio": precio or 0,
            "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
            "area_m2": area,
            "fuente": "clasificado",
            "fuente_detalle": "Urbania",
            "url": href or url,
            "distrito": guess_distrito(text),
        })

    return results


# ============================================================
# MAIN
# ============================================================

def scrape_all_portales():
    """Run all portal scrapers and insert results into DB."""
    conn = get_db()
    total_new = 0

    # Map portal names to scraper functions
    scraper_map = {
        "nestoria": scrape_nestoria,
        "laencontre": scrape_laencontre,
        "properati": scrape_properati,
        "urbania": scrape_urbania,
    }

    scrapers = []
    for portal_name, url, modo in PORTAL_URLS:
        fn = scraper_map.get(portal_name)
        if fn:
            label = f"{portal_name.title()} {modo}"
            scrapers.append((label, fn, url, modo))

    for name, scraper_fn, url, modo in scrapers:
        log.info(f"Scraping: {name}")
        try:
            results = scraper_fn(url, modo)
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
                (name, modo, len(results), new_count),
            )
            conn.commit()
        except Exception as e:
            log.error(f"  {name} failed: {e}")

    close_browser()
    conn.close()
    return total_new


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    total = scrape_all_portales()
    print(f"Total new properties: {total}")
