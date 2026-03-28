#!/bin/bash
# setup-nanobot.sh — Install and configure nanobot on RPi 5
# Run on the Pi: bash ~/homelab/benchmark/setup-nanobot.sh

set -euo pipefail

HOMELAB_DIR="$HOME/homelab"
BENCHMARK_DIR="$HOMELAB_DIR/benchmark"
NANOBOT_DIR="$HOMELAB_DIR/nanobot"

echo "=== 1. Install nanobot ==="
pip install --break-system-packages nanobot-ai 2>/dev/null || pip install nanobot-ai

echo "=== 2. Create nanobot directory ==="
mkdir -p "$NANOBOT_DIR"

echo "=== 3. Create .env file ==="
if [ ! -f "$NANOBOT_DIR/.env" ]; then
    cat > "$NANOBOT_DIR/.env" << 'EOF'
# nanobot config — fill in before starting
TELEGRAM_BOT_TOKEN=your_second_bot_token_here
GOOGLE_API_KEY=same_as_openclaw
GROQ_API_KEY=same_as_openclaw
CEREBRAS_API_KEY=same_as_openclaw

# Benchmark reaction collector
BENCHMARK_OC_BOT_TOKEN=openclaw_bot_token
BENCHMARK_NB_BOT_TOKEN=nanobot_bot_token
EOF
    echo "  .env created at $NANOBOT_DIR/.env — EDIT before continuing"
else
    echo "  .env already exists, skipping"
fi

echo "=== 4. Copy skills ==="
SKILLS_SRC="$BENCHMARK_DIR/skills"
SKILLS_DST="$NANOBOT_DIR/skills"
mkdir -p "$SKILLS_DST"

for skill in adguard wifi-devices bt-devices rpi-health; do
    mkdir -p "$SKILLS_DST/$skill"
    if [ -f "$SKILLS_SRC/$skill/SKILL.md" ]; then
        cp "$SKILLS_SRC/$skill/SKILL.md" "$SKILLS_DST/$skill/"
        echo "  Copied $skill/SKILL.md"
    fi
done

# Symlink shared scripts (no duplication)
echo "=== 5. Link shared scripts ==="
ln -sf "$HOMELAB_DIR/openclaw/custom-skills/adguard-home/scripts" "$SKILLS_DST/adguard/scripts" 2>/dev/null || true
ln -sf "$HOMELAB_DIR/openclaw/custom-skills/wifi-devices/scripts" "$SKILLS_DST/wifi-devices/scripts" 2>/dev/null || true
ln -sf "$HOMELAB_DIR/openclaw/custom-skills/bt-devices/scripts" "$SKILLS_DST/bt-devices/scripts" 2>/dev/null || true
ln -sf "$HOMELAB_DIR/scripts" "$SKILLS_DST/rpi-health/scripts" 2>/dev/null || true

echo "=== 6. Create systemd service ==="
sudo tee /etc/systemd/system/nanobot-gateway.service > /dev/null << EOF
[Unit]
Description=nanobot Telegram Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=cristian
WorkingDirectory=$NANOBOT_DIR
EnvironmentFile=$NANOBOT_DIR/.env
ExecStart=$(which nanobot 2>/dev/null || echo "/home/cristian/.local/bin/nanobot") serve --port 18790
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "=== 7. Init benchmark DB ==="
python3 "$BENCHMARK_DIR/init-db.py"

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. Edit $NANOBOT_DIR/.env with real tokens"
echo "  2. Run: nanobot onboard (if needed)"
echo "  3. Run: sudo systemctl daemon-reload"
echo "  4. Run: sudo systemctl enable --now nanobot-gateway"
echo "  5. Test: send a message to @Buho2_bot"
