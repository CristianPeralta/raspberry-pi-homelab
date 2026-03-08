"""Housing Hunter — Scraper de portales peruanos adicionales.

ubicasa.pe: Next.js SSR — JSON embebido en HTML (initialProperties)
infocasas.com.pe: Next.js + Apollo — JSON en __NEXT_DATA__
adondevivir.com: SSR — requiere UA de browser real (403 sin él)
"""

import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from config import HEADERS, PORTAL_PE_URLS, ALQUILER_MAX_PEN, VENTA_MAX_USD, get_db, insert_property
from config import guess_distrito as _guess_distrito_cfg

log = logging.getLogger("housing.portales_pe")

# Extra headers for adondevivir (returns 403 without Referer)
ADV_HEADERS = {
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


def _guess_tipo(text):
    t = text.lower()
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "casa" in t:
        return "casa"
    if "depa" in t or "departamento" in t:
        return "departamento"
    if "habitacion" in t or "cuarto" in t:
        return "habitacion"
    if "local" in t:
        return "local"
    return "otro"


def _guess_distrito(text):
    return _guess_distrito_cfg(text)


def _filter_budget(modo, precio, moneda):
    if precio is None or precio == 0:
        return True
    if modo == "alquiler" and moneda == "PEN" and precio > ALQUILER_MAX_PEN:
        return False
    if modo == "venta" and moneda == "USD" and precio > VENTA_MAX_USD:
        return False
    if modo == "venta" and moneda == "PEN" and precio > VENTA_MAX_USD * 4:
        return False
    return True


# ============================================================
# UBICASA.PE — JSON embebido (initialProperties)
# ============================================================

UBICASA_URLS = [(url, modo) for name, url, modo in PORTAL_PE_URLS if name == "ubicasa"]


def scrape_ubicasa(url, modo):
    """Scrape ubicasa.pe by extracting initialProperties JSON from HTML."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"ubicasa fetch failed {url}: {e}")
        return []

    results = []

    # ubicasa uses React Server Components (RSC) with escaped JSON in HTML
    # The data is in escaped form: \"propertyId\" inside script chunks
    # Strategy: unescape the HTML, then extract each property object by propertyId anchor

    unescaped = resp.text.replace('\\"', '"')
    properties = []

    for m in re.finditer(r'\{"propertyId":"([^"]+)"', unescaped):
        start = m.start()
        # Bracket-match to find complete object (handles nested objects)
        depth = 0
        end = start
        for i, c in enumerate(unescaped[start:start+5000]):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            if depth == 0:
                end = start + i + 1
                break
        block = unescaped[start:end]
        # Clean RSC placeholders like "$12" that aren't valid JSON
        block = re.sub(r'"\$\d+"', 'null', block)
        try:
            obj = json.loads(block)
            properties.append(obj)
        except json.JSONDecodeError:
            continue

    log.info(f"  ubicasa: extracted {len(properties)} properties from RSC")

    for p in properties:
            title = p.get("title", "")
            if not title:
                continue

            # Price
            price_obj = p.get("price", {})
            if isinstance(price_obj, dict):
                precio_pen = price_obj.get("soles")
                precio_usd = price_obj.get("dollars")
                if modo == "alquiler" and precio_pen:
                    precio, moneda = float(precio_pen), "PEN"
                elif precio_usd:
                    precio, moneda = float(precio_usd), "USD"
                elif precio_pen:
                    precio, moneda = float(precio_pen), "PEN"
                else:
                    precio, moneda = 0, "PEN" if modo == "alquiler" else "USD"
            else:
                precio, moneda = 0, "PEN" if modo == "alquiler" else "USD"

            if not _filter_budget(modo, precio, moneda):
                continue

            # Details
            details = p.get("details", {})
            area = details.get("totalArea") or details.get("builtArea")
            rooms = details.get("bedrooms")
            banos = details.get("bathrooms")

            # Location
            loc = p.get("location", {})
            distrito = loc.get("admin_level_3") or _guess_distrito(title)
            direccion = loc.get("address")

            # URL
            slug = p.get("slug", "")
            prop_url = f"https://ubicasa.pe/inmuebles/{slug}" if slug else url

            results.append({
                "modo": modo,
                "tipo": _guess_tipo(title),
                "titulo": title[:200],
                "precio": precio,
                "moneda": moneda,
                "area_m2": float(area) if area else None,
                "habitaciones": int(rooms) if rooms else None,
                "banos": int(banos) if banos else None,
                "distrito": distrito,
                "direccion": direccion,
                "fuente": "clasificado",
                "fuente_detalle": "Ubicasa",
                "url": prop_url,
            })

    return results


# ============================================================
# INFOCASAS.COM.PE — Apollo GraphQL state in __NEXT_DATA__
# ============================================================

INFOCASAS_URLS = [(url, modo) for name, url, modo in PORTAL_PE_URLS if name == "infocasas"]


def scrape_infocasas(url, modo):
    """Scrape infocasas.com.pe by extracting Apollo state from __NEXT_DATA__."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"infocasas fetch failed {url}: {e}")
        return []

    results = []

    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not nd:
        log.warning(f"infocasas: no __NEXT_DATA__ found at {url}")
        return []

    try:
        data = json.loads(nd.group(1))
    except json.JSONDecodeError as e:
        log.error(f"infocasas JSON parse error: {e}")
        return []

    page_props = data.get("props", {}).get("pageProps", {})

    # Primary path: fetchResult.searchFast.data
    properties = []
    fetch_result = page_props.get("fetchResult", {})
    search_fast = fetch_result.get("searchFast", {})
    if isinstance(search_fast, dict):
        properties = search_fast.get("data", [])

    # Fallback: apolloState
    if not properties:
        apollo = page_props.get("apolloState", {})
        for key, val in apollo.items():
            if isinstance(val, dict) and "data" in val:
                items = val["data"]
                if isinstance(items, list) and items:
                    if any(isinstance(i, dict) and ("title" in i or "price" in i) for i in items):
                        properties = items
                        break

    for p in properties:
        if not isinstance(p, dict):
            continue

        title = p.get("title", "")
        if not title:
            continue

        # Price — infocasas uses {amount: N, currency: {id, name, rate}}
        price_obj = p.get("price", {})
        if isinstance(price_obj, dict):
            amount = price_obj.get("amount")
            curr_obj = price_obj.get("currency", {})
            if isinstance(curr_obj, dict):
                curr_name = curr_obj.get("name", "")
                moneda = "USD" if "US" in curr_name or "$" == curr_name else "PEN"
            elif isinstance(curr_obj, str):
                moneda = "USD" if curr_obj == "USD" else "PEN"
            else:
                moneda = "PEN" if modo == "alquiler" else "USD"
            precio = float(amount) if amount else 0
        else:
            precio, moneda = 0, "PEN" if modo == "alquiler" else "USD"

        if not _filter_budget(modo, precio, moneda):
            continue

        area = p.get("m2Built") or p.get("m2Terrain") or p.get("m2")
        rooms = p.get("bedrooms") or p.get("rooms")
        banos = p.get("bathrooms")

        # Location — infocasas uses nested arrays: neighbourhood: [{name: "X"}]
        locs = p.get("locations", {})
        neigh = locs.get("neighbourhood", [])
        if isinstance(neigh, list) and neigh:
            distrito = neigh[0].get("name") if isinstance(neigh[0], dict) else None
        elif isinstance(neigh, dict):
            distrito = neigh.get("name")
        else:
            distrito = None
        if not distrito:
            distrito = _guess_distrito(title)

        # URL
        link = p.get("link", "")
        prop_url = f"https://www.infocasas.com.pe{link}" if link else url

        results.append({
            "modo": modo,
            "tipo": _guess_tipo(title),
            "titulo": title[:200],
            "precio": precio,
            "moneda": moneda,
            "area_m2": float(area) if area else None,
            "habitaciones": int(rooms) if rooms else None,
            "banos": int(banos) if banos else None,
            "distrito": distrito,
            "fuente": "clasificado",
            "fuente_detalle": "InfoCasas",
            "url": prop_url,
        })

    return results


# ============================================================
# ADONDEVIVIR.COM — SSR HTML (needs browser UA)
# ============================================================

ADONDEVIVIR_URLS = [(url, modo) for name, url, modo in PORTAL_PE_URLS if name == "adondevivir"]


def _get_browser():
    """Get or create a Playwright browser (reuses scrape_portales browser)."""
    try:
        from scrape_portales import get_browser
        return get_browser()
    except ImportError:
        return None


def _fetch_with_playwright(url):
    """Fetch URL with Playwright, return HTML text."""
    browser = _get_browser()
    if not browser:
        return None
    try:
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            locale="es-PE",
        )
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        html = page.content()
        page.close()
        return html
    except Exception as e:
        log.error(f"Playwright fetch failed {url}: {e}")
        return None


def scrape_adondevivir(url, modo):
    """Scrape adondevivir.com — requires Playwright (403 with plain requests)."""
    # Try requests first (fast), fall back to Playwright
    html = None
    try:
        resp = requests.get(url, headers=ADV_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        log.info(f"adondevivir: requests failed, trying Playwright for {url}")
        html = _fetch_with_playwright(url)

    if not html:
        log.error(f"adondevivir: could not fetch {url}")
        return []

    results = []
    soup = BeautifulSoup(html, "html.parser")

    # Try __NEXT_DATA__ first (it's a Next.js app too)
    nd = soup.select_one('script#__NEXT_DATA__')
    if nd:
        try:
            data = json.loads(nd.string)
            page_props = data.get("props", {}).get("pageProps", {})
            # Look for listing data in various keys
            listings = []
            for key in ("listPostings", "initialPostings", "postings", "results"):
                if key in page_props:
                    val = page_props[key]
                    if isinstance(val, dict) and "data" in val:
                        listings = val["data"]
                    elif isinstance(val, list):
                        listings = val
                    break

            for p in listings:
                if not isinstance(p, dict):
                    continue
                title = p.get("title") or p.get("address") or ""
                if not title:
                    continue

                # Price
                price_obj = p.get("price") or p.get("priceOperationType", {})
                if isinstance(price_obj, dict):
                    precio = float(price_obj.get("amount", 0))
                    moneda = "USD" if price_obj.get("currency") == "USD" else "PEN"
                elif isinstance(price_obj, (int, float)):
                    precio = float(price_obj)
                    moneda = "PEN" if modo == "alquiler" else "USD"
                else:
                    precio, moneda = 0, "PEN" if modo == "alquiler" else "USD"

                if not _filter_budget(modo, precio, moneda):
                    continue

                area = p.get("floorPlan") or p.get("surface") or p.get("totalSurface")
                rooms = p.get("bedrooms") or p.get("rooms")

                link = p.get("url") or p.get("link") or ""
                if link and not link.startswith("http"):
                    link = "https://www.adondevivir.com" + link

                loc_parts = []
                for lk in ("locationPath", "address", "neighborhood", "city"):
                    if lk in p and p[lk]:
                        loc_parts.append(str(p[lk]))
                loc_text = " ".join(loc_parts) or title

                results.append({
                    "modo": modo,
                    "tipo": _guess_tipo(title),
                    "titulo": title[:200],
                    "precio": precio,
                    "moneda": moneda,
                    "area_m2": float(area) if area else None,
                    "habitaciones": int(rooms) if rooms else None,
                    "distrito": _guess_distrito(loc_text),
                    "fuente": "clasificado",
                    "fuente_detalle": "AdondeVivir",
                    "url": link or url,
                })

            if results:
                return results
        except json.JSONDecodeError:
            pass

    # Fallback: parse HTML cards
    selectors = [
        "[data-qa=posting]", "[class*=postingCard]", "[class*=CardContainer]",
        ".posting-card", "article", "[class*=Posting]",
    ]
    listings = []
    for sel in selectors:
        listings = soup.select(sel)
        if listings:
            break

    # Last resort: divs with price-like content
    if not listings:
        for div in soup.find_all("div", class_=True):
            text = div.get_text()
            if re.search(r"S/|USD|\$", text) and re.search(r"m[²2]|hab|dorm", text, re.I):
                listings.append(div)

    for item in listings:
        text = item.get_text(separator=" ", strip=True)
        if len(text) < 15:
            continue

        title_el = item.select_one("h2, h3, [class*=title], [class*=Title], [class*=address]")
        title = title_el.get_text(strip=True) if title_el else text[:100]

        price_text = text
        price_el = item.select_one("[class*=price], [class*=Price], [data-qa*=price]")
        if price_el:
            price_text = price_el.get_text()

        precio, moneda = _extract_price_html(price_text)
        if not _filter_budget(modo, precio, moneda):
            continue

        area_m = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]?", text)
        area = float(area_m.group(1)) if area_m else None

        link_el = item.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.adondevivir.com" + href

        results.append({
            "modo": modo,
            "tipo": _guess_tipo(text),
            "titulo": title[:200],
            "precio": precio or 0,
            "moneda": moneda or ("PEN" if modo == "alquiler" else "USD"),
            "area_m2": area,
            "fuente": "clasificado",
            "fuente_detalle": "AdondeVivir",
            "url": href or url,
            "distrito": _guess_distrito(text),
        })

    return results


def _extract_price_html(text):
    """Extract price from HTML text."""
    if not text:
        return None, None
    clean = text.replace(",", "")
    m = re.search(r"(?:US?\$|USD)\s*([\d.]+)", clean)
    if m:
        return float(m.group(1).rstrip(".")), "USD"
    m = re.search(r"(?:S/?\.?\s*)([\d.]+)", clean)
    if m:
        return float(m.group(1).rstrip(".")), "PEN"
    return None, None


# ============================================================
# MAIN
# ============================================================

def scrape_all_portales_pe():
    """Run all Peruvian portal scrapers and insert results into DB."""
    conn = get_db()
    total_new = 0

    scrapers = []

    for url, modo in UBICASA_URLS:
        scrapers.append((f"Ubicasa {modo}", scrape_ubicasa, url, modo))

    for url, modo in INFOCASAS_URLS:
        scrapers.append((f"InfoCasas {modo}", scrape_infocasas, url, modo))

    for url, modo in ADONDEVIVIR_URLS:
        scrapers.append((f"AdondeVivir {modo}", scrape_adondevivir, url, modo))

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

    # Close Playwright browser if it was started for adondevivir
    try:
        from scrape_portales import close_browser
        close_browser()
    except ImportError:
        pass

    conn.close()
    return total_new


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    total = scrape_all_portales_pe()
    print(f"Total new from PE portals: {total}")
