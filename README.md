# Raspberry Pi 5 Homelab

Self-hosted homelab running on a Raspberry Pi 5 16GB with NVMe SSD.

## Services

| Service | Port | Description |
|---|---|---|
| [OpenClaw](https://openclaw.ai/) | 3000 | AI assistant hub (Claude, GPT, Gemini) |
| Home Assistant | 8123 | Home automation (coming soon) |
| Frigate NVR | 5000 | Video surveillance (coming soon) |

## Hardware

- Raspberry Pi 5 16GB RAM
- NVMe SSD 512GB (M.2 HAT+)
- Official case with Active Cooler

## Quick Start

```bash
# Clone this repo on your Pi
git clone https://github.com/CristianPeralta/raspberry-pi-homelab.git ~/homelab
cd ~/homelab

# Set up OpenClaw
cd openclaw
cp .env.example .env
# Edit .env with your API keys
nano .env

# Start
docker compose up -d
```

## Health Check

```bash
./scripts/health.sh
```

## Structure

```
.
├── openclaw/
│   ├── docker-compose.yml
│   └── .env.example
├── homeassistant/        (coming soon)
├── frigate/              (coming soon)
└── scripts/
    └── health.sh
```
