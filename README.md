# Raspberry Pi 5 Homelab

Operational snapshot of the services hosted on a Raspberry Pi 5. The state below was verified directly on the host on **2026-08-12**.

## Host status

| Item | Current state |
|---|---|
| Host | `homelab`, Raspberry Pi 5, ARM64 |
| OS | Debian 13 (trixie), Linux `6.12.62+rpt-rpi-2712` |
| Memory | 16 GB |
| System disk | 512 GB NVMe, 16% used |
| Media disk | 1 TB USB HDD mounted at `/mnt/media` |
| LAN | WiFi `192.168.100.30/24` |
| Guest network | Ethernet gateway `192.168.50.1/24` |
| Remote access | Tailscale |

## Running services

### Docker Compose

| Project | Services | Access | Purpose |
|---|---|---|---|
| `repo` | OpenClaw gateway | `18789-18790` | Main Telegram AI assistant and homelab skills |
| `nanobot` | NanoBot | Internal | Experimental lightweight AI agent |
| `litellm` | LiteLLM, PostgreSQL | `4000` | Shared LLM gateway and persistence |
| `adguard` | AdGuard Home | `53`, `80` | DNS filtering and DHCP for the guest network |
| `media` | Jellyfin, Sonarr, Radarr, Prowlarr, qBittorrent | `8096`, `8989`, `7878`, `9696`, `8080` | Media library and download automation |
| `stremio` | Stremio | `8082` | Media streaming service |
| `n8n` | n8n | `5678` | Workflow automation |
| `obs-agent` | cAdvisor, node-exporter, Promtail | `8081`, `9100`, internal | Metrics and log collection |
| `mantys-bot` | Moonraker Telegram bot | Internal | Remote monitoring and control for the MANTYS printer |

### Systemd

| Unit | Scope | State | Purpose |
|---|---|---|---|
| `docker.service` | System | Active, enabled | Container runtime |
| `tailscaled.service` | System | Active, enabled | Private remote network |
| `ping-server.service` | System | Active, enabled | WiFi and Bluetooth device history API on `8888` |
| `guest-network-firewall.service` | System | Active, enabled | Guest network isolation and NAT |
| `hermes-gateway.service` | User | Active, enabled | Hermes messaging gateway |
| `hermes-serve.service` | User | Active, enabled | Hermes endpoint on the Tailscale address, port `9119` |

## Paused services

| Service | Current state | Notes |
|---|---|---|
| Minecraft server | Container stopped on 2026-08-03 | Data and Compose configuration remain under `/home/cristian/homelab/minecraft` |
| Buho Minecraft agent | Container stopped on 2026-08-03 | The `minecraft-bot` project and its state remain on the host; Buho is intentionally paused, not removed |
| OpenBuho benchmark workspace | Not installed | No `.openclaw-bench` workspace or listener on `18791` was present during verification |

## Scheduled operations

- WiFi discovery and health monitoring every 5 minutes.
- Bluetooth discovery every 30 minutes.
- Benchmark reaction collection every 10 minutes.
- Media stalled-download guard every 30 minutes.
- Daily Restic backup at 03:30.
- Daily Legimus research, task schedule notifications, finance sync, weekly-plan checks, and a Herdr watchdog.

## Network layout

```text
Main LAN (WiFi 192.168.100.0/24)
  └── Raspberry Pi: 192.168.100.30
        ├── Tailscale: 100.83.205.49
        └── Guest gateway (Ethernet): 192.168.50.1/24
              └── AdGuard DHCP/DNS + firewall/NAT isolation
```

## Repository scope

This repository documents the homelab and contains selected deployment files. The live tree at `/home/cristian/homelab` is **not a Git checkout** and includes additional private runtime configuration that is intentionally excluded from this repository.

Tracked components include:

```text
.
├── adguard/          # AdGuard Home Compose definition
├── openclaw/         # OpenClaw Compose definition and environment example
├── housing-hunter/   # Property search automation
├── scripts/          # Host health helper
├── systemd/          # ping-server unit
└── crontab.txt       # Historical/sanitized cron reference
```

Secrets, live data, agent workspaces, media, databases, and backup repositories must remain on the host and outside Git.

## Verification

The snapshot was built from read-only checks over SSH: host/network/storage status, `systemctl`, user services, timers, crontab schedules, `docker ps -a`, `docker compose ls -a`, listening ports, and the Minecraft/Buho Compose state. No credentials or runtime configuration values were copied.
