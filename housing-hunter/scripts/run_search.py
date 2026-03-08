#!/usr/bin/env python3
"""Housing Hunter — Entry point: scrape all sources + notify."""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Ensure script dir is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scrape_portales import scrape_all_portales
from scrape_portales_pe import scrape_all_portales_pe
from scrape_facebook import scrape_all_facebook
from scrape_periodicos import scrape_all_periodicos
from notify import notify_new_properties, send_daily_summary
from gen_dashboard_md import main as gen_dashboard
from config import LOG_DIR

def setup_logging():
    log_file = LOG_DIR / f"search-{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

def main():
    setup_logging()
    log = logging.getLogger("housing.main")

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    log.info(f"=== Housing Hunter search started (mode={mode}) ===")

    total_new = 0

    if mode in ("all", "portales"):
        log.info("--- Scraping portales internacionales ---")
        total_new += scrape_all_portales()

    if mode in ("all", "portales", "portales_pe"):
        log.info("--- Scraping portales peruanos (ubicasa, infocasas, adondevivir) ---")
        total_new += scrape_all_portales_pe()

    if mode in ("all", "facebook"):
        log.info("--- Scraping Facebook groups ---")
        total_new += scrape_all_facebook()

    if mode in ("all", "periodicos"):
        log.info("--- Scraping periodicos ---")
        total_new += scrape_all_periodicos()

    log.info(f"Total new properties found: {total_new}")

    if mode in ("all", "portales", "portales_pe", "facebook", "periodicos"):
        if total_new > 0:
            log.info("--- Sending Telegram notifications ---")
            notify_new_properties()
        else:
            log.info("No new properties, skipping notification")

    if mode == "daily":
        log.info("--- Sending daily summary ---")
        send_daily_summary()

    if mode == "notify":
        notify_new_properties()

    # Regenerate Obsidian dashboard after any search or on demand
    if mode in ("all", "portales", "portales_pe", "facebook", "periodicos", "dashboard"):
        log.info("--- Regenerating propiedades.md ---")
        gen_dashboard()

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
