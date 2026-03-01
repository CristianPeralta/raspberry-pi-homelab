---
name: rpi-health
description: Check Raspberry Pi 5 health and system status. Use when the user asks about temperature, system health, memory, disk, uptime, load, or server status. Triggers on keywords like "health", "temperatura", "temp", "salud", "estado del servidor", "memoria", "disco", "uptime", "carga", "load", "how is the pi", "como esta la pi".
---

# Raspberry Pi 5 Health

Check system health metrics of the Raspberry Pi.

## Script

```bash
bash /app/skills/rpi-health/scripts/health.sh <command>
```

## Commands

- `status` — Full health overview (default)
- `temp` — CPU temperature only
- `mem` — RAM usage
- `disk` — Disk usage
- `uptime` — System uptime
- `load` — CPU load average

## Examples

### Full health check
```bash
bash /app/skills/rpi-health/scripts/health.sh status
```

### Temperature only
```bash
bash /app/skills/rpi-health/scripts/health.sh temp
```

## Response Format (Telegram)

- Show the output directly, it's already formatted for chat
- Use Spanish
- If temp > 70°C warn the user
- If RAM > 80% or Disk > 80% warn the user
