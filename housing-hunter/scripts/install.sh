#!/bin/bash
# Housing Hunter — Install dependencies + cron jobs
# Usage: bash install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
ENV_FILE="$SCRIPT_DIR/.env"

echo "=== Housing Hunter Setup ==="
echo "Script dir: $SCRIPT_DIR"
echo "Python: $PYTHON"

# 1. Install Python deps
echo ""
echo "--- Installing Python dependencies ---"
pip3 install --quiet requests beautifulsoup4 facebook-scraper lxml_html_clean pyyaml

# 2. Verify
echo "--- Verifying ---"
$PYTHON -c "import requests, bs4; print('Dependencies OK')"

# 3. Setup .env for Telegram
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "--- Configuring Telegram ---"
    read -p "TELEGRAM_BOT_TOKEN: " BOT_TOKEN
    read -p "TELEGRAM_CHAT_ID: " CHAT_ID
    cat > "$ENV_FILE" << EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_CHAT_ID=$CHAT_ID
EOF
    chmod 600 "$ENV_FILE"
    echo ".env created at $ENV_FILE"
else
    echo ".env already exists at $ENV_FILE"
fi

# 4. Install cron jobs
echo ""
echo "--- Installing cron jobs ---"

# Remove existing housing-hunter cron entries
crontab -l 2>/dev/null | grep -v "housing-hunter" | grep -v "run_search.py" > /tmp/cron_clean 2>/dev/null || true

# Add new entries (source .env before each run)
cat >> /tmp/cron_clean << CRON
# housing-hunter: scrape portales cada 6 horas (6am, 12pm, 6pm, 12am)
0 6,12,18,0 * * * cd $SCRIPT_DIR && set -a && . .env && set +a && $PYTHON run_search.py portales >> logs/cron.log 2>&1

# housing-hunter: scrape facebook groups 2 veces al dia (7am, 1pm)
0 7,13 * * * cd $SCRIPT_DIR && set -a && . .env && set +a && $PYTHON run_search.py facebook >> logs/cron.log 2>&1

# housing-hunter: scrape periodicos 2 veces al dia (8am, 2pm)
0 8,14 * * * cd $SCRIPT_DIR && set -a && . .env && set +a && $PYTHON run_search.py periodicos >> logs/cron.log 2>&1

# housing-hunter: resumen diario a las 9pm
0 21 * * * cd $SCRIPT_DIR && set -a && . .env && set +a && $PYTHON run_search.py daily >> logs/cron.log 2>&1
CRON

crontab /tmp/cron_clean
rm /tmp/cron_clean

echo "Cron jobs installed:"
crontab -l | grep "housing-hunter"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Schedule:"
echo "  - Portales: cada 6h (6am, 12pm, 6pm, 12am)"
echo "  - Periodicos: 2x dia (8am, 2pm)"
echo "  - Resumen diario: 9pm"
echo ""
echo "Manual run:"
echo "  cd $SCRIPT_DIR && set -a && . .env && set +a && python3 run_search.py all"
echo "  cd $SCRIPT_DIR && python3 run_search.py portales  # solo portales (sin Telegram)"
echo "  cd $SCRIPT_DIR && python3 run_search.py daily     # resumen diario"
echo "  cd $SCRIPT_DIR && python3 run_search.py notify    # re-enviar notificaciones"
