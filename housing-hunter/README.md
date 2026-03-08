# Housing Hunter

Automated property search system for rental and purchase listings in Peru. Scrapes real estate portals, local newspapers, and Facebook groups, then sends Telegram alerts for new properties.

## Features

- **Multi-source scraping**: Nestoria, LaEncontre, Properati, Urbania (Playwright), Ubicasa, InfoCasas (JSON extraction), Facebook groups
- **Budget filtering**: Configurable max rent / max purchase price
- **Telegram alerts**: Instant notifications for new properties + daily summary
- **SQLite tracking**: Deduplication, status pipeline (nueva → contactada → visitada → negociando → descartada)
- **Obsidian dashboard**: Auto-generated markdown for property tracking
- **CLI dashboard**: Terminal-based property viewer with ANSI colors
- **Cron automation**: Configurable scraping schedule

## Setup

```bash
cd scripts

# Install dependencies
pip3 install requests beautifulsoup4 playwright pyyaml facebook-scraper lxml_html_clean
playwright install chromium
playwright install-deps chromium

# Configure
cp config.yaml.example config.yaml  # Edit with your search preferences

# Set up Telegram credentials
cat > .env << EOF
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
EOF
chmod 600 .env

# Initialize database
python3 -c "
import sqlite3
conn = sqlite3.connect('../db/housing.db')
conn.executescript(open('../db/schema.sql').read())
conn.executescript(open('../db/seed.sql').read())
conn.close()
"

# Install cron jobs
bash install.sh
```

## Usage

```bash
# Run all scrapers
python3 run_search.py all

# Run specific sources
python3 run_search.py portales      # International + PE portals
python3 run_search.py portales_pe   # Only Peruvian portals (Ubicasa, InfoCasas)
python3 run_search.py facebook      # Facebook groups (requires fb_cookies.txt)
python3 run_search.py periodicos    # Local newspapers

# Notifications
python3 run_search.py daily         # Send daily summary via Telegram
python3 run_search.py notify        # Re-send pending notifications

# Dashboard
python3 run_search.py dashboard     # Regenerate Obsidian markdown
python3 dashboard.py                # CLI dashboard
python3 dashboard.py detalle 5      # Property detail
python3 dashboard.py descartar 5 "too expensive"  # Discard property
```

## Configuration

All personal preferences go in `config.yaml` (gitignored). See `config.yaml.example` for the template.

Configurable:
- City and districts of interest
- Budget limits (rent/purchase)
- Portal URLs to scrape
- Facebook groups to monitor
- Local newspapers
- Dashboard display settings

## Facebook Groups

Facebook groups require authentication. To enable:

1. Install browser extension "Get cookies.txt LOCALLY"
2. Log into Facebook, export cookies
3. Save as `scripts/fb_cookies.txt`

Use a secondary account to reduce ban risk.

## Architecture

```
housing-hunter/
├── scripts/
│   ├── config.py              # Config loader (reads config.yaml + .env)
│   ├── config.yaml.example    # Template (committed)
│   ├── scrape_portales.py     # Nestoria (HTML) + LaEncontre/Properati/Urbania (Playwright)
│   ├── scrape_portales_pe.py  # Ubicasa (RSC JSON) + InfoCasas (__NEXT_DATA__)
│   ├── scrape_facebook.py     # Facebook groups (facebook-scraper)
│   ├── scrape_periodicos.py   # Local newspapers (HTML)
│   ├── notify.py              # Telegram notifications
│   ├── gen_dashboard_md.py    # Obsidian markdown generator
│   ├── dashboard.py           # CLI dashboard
│   ├── run_search.py          # Entry point
│   └── install.sh             # Dependency + cron installer
└── db/
    ├── schema.sql             # Database schema
    └── seed.sql               # Initial data (zones, programs)
```

## Cron Schedule

| Task | Frequency | Time |
|------|-----------|------|
| Portal scraping | 4x/day | 6am, 12pm, 6pm, 12am |
| Facebook groups | 2x/day | 7am, 1pm |
| Newspapers | 2x/day | 8am, 2pm |
| Daily summary | 1x/day | 9pm |
