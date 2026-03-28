---
name: rpi-health
description: Check Raspberry Pi 5 health and system status. Triggers on keywords like "health", "temperatura", "temp", "salud", "estado del servidor", "memoria", "disco", "uptime", "carga", "load", "how is the pi", "como esta la pi".
---

# Raspberry Pi 5 Health

Check system health metrics of the Raspberry Pi.

## Script

```bash
bash {baseDir}/scripts/health.sh
```

## Response Format (Telegram)

- Show the output directly, it's already formatted for chat
- Use Spanish
- If temp > 70C warn the user
- If RAM > 80% or Disk > 80% warn the user
