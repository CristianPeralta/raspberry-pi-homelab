# Raspberry Pi 5 Homelab

Self-hosted homelab running on a Raspberry Pi 5 16GB with NVMe SSD boot.

## Services

| Service | Port | Description |
|---|---|---|
| [OpenClaw](https://openclaw.ai/) | 3000 | AI assistant via Telegram (multi-model: Gemini, Groq, Cerebras, Mistral) |
| [AdGuard Home](https://adguard.com/adguard-home.html) | 80 | Network-wide DNS ad/tracker blocker |
| ping-server | 8888 | LAN device scanner + SQLite history (systemd) |

## Custom Skills (Telegram Bot)

The OpenClaw bot is controlled via Telegram. Custom skills extend its capabilities:

| Skill | Trigger | Description |
|---|---|---|
| wifi-devices | `/wifi` | Scan which devices are online on the LAN |
| bt-devices | `/bt` | Discover nearby Bluetooth devices |
| adguard-home | `/adguard` | Control AdGuard Home (block/unblock sites, stats, parental controls) |
| rpi-health | `/health` | System health (CPU, RAM, disk, temp) |

### Device History

The ping-server maintains a SQLite database that logs every WiFi and BT scan automatically (cron: WiFi every 5min, BT every 30min). Query from Telegram:

- "who was home today?" → presence ranges per device
- "when was Roxsy last seen?" → last detection with relative times
- "list devices" → all registered devices

## Hardware

- Raspberry Pi 5 16GB RAM
- NVMe SSD 512GB (BIWIN CE430T5D100, M.2 HAT+)
- Official case with Active Cooler

## Quick Start

```bash
# Clone on your Pi
git clone https://github.com/CristianPeralta/raspberry-pi-homelab.git ~/homelab
cd ~/homelab

# AdGuard Home
cd adguard
docker compose up -d

# OpenClaw
cd ../openclaw
cp .env.example .env
# Edit .env with your API keys
docker compose up -d

# Ping server (device scanner)
sudo cp systemd/ping-server.service /etc/systemd/system/
# Edit the service file to match your paths
sudo systemctl daemon-reload
sudo systemctl enable --now ping-server

# Cron for automatic scanning
crontab crontab.txt
```

## Structure

```
.
├── adguard/
│   └── docker-compose.yml
├── openclaw/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── custom-skills/
│       ├── adguard-home/
│       │   ├── scripts/adguard-ctl.sh
│       │   └── SKILL.md
│       ├── bt-devices/
│       │   ├── scripts/bt-devices.sh
│       │   └── SKILL.md
│       ├── wifi-devices/
│       │   ├── scripts/ping-server.py
│       │   ├── scripts/wifi-devices.sh
│       │   └── SKILL.md
│       └── rpi-health/
│           ├── scripts/health.sh
│           └── SKILL.md
├── systemd/
│   └── ping-server.service
├── scripts/
│   └── health.sh
└── crontab.txt
```

## API Endpoints (ping-server)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/scan` | Ping all WiFi devices, log to DB |
| GET | `/scan?minutes=N` | Same + DNS activity from AdGuard |
| GET | `/bt-scan` | Bluetooth discovery + known devices |
| GET | `/devices` | List all registered devices |
| POST | `/devices` | Add/update device |
| DELETE | `/devices?id=N` | Remove device |
| GET | `/logs/last-seen` | Last detection per device |
| GET | `/logs/presence?hours=N` | Presence timeline |
