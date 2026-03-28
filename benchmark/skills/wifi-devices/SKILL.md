---
name: wifi-devices
description: Scan which devices are currently online on the home WiFi network. Triggers on keywords like "conectados", "activos", "quien esta", "wifi", "dispositivos activos", "en la red", "online", "quienes estan", "hay alguien".
---

# WiFi Devices Scanner

When the user asks who is connected, IMMEDIATELY execute this and format the output:

```bash
bash {baseDir}/scripts/wifi-devices.sh active
```

For activity with DNS data (last N minutes):
```bash
bash {baseDir}/scripts/wifi-devices.sh active 30
```

## Additional Commands

| Command | When to use |
|---|---|
| `devices` | User asks to list/see all registered devices |
| `last-seen` | User asks "when was X last seen?" or "ultima vez" |
| `history [hours]` | User asks "who was home today?", "presencia", "historial" |
| `add-device JSON` | User wants to register a new device |

Examples:
```bash
bash {baseDir}/scripts/wifi-devices.sh devices
bash {baseDir}/scripts/wifi-devices.sh last-seen
bash {baseDir}/scripts/wifi-devices.sh history 12
bash {baseDir}/scripts/wifi-devices.sh add-device '{"name":"TV-Sala","type":"tv","wifi_ip":"192.168.1.50"}'
```

Do NOT ask for confirmation. Just run the command and show results.
Use green circle for online, red circle for offline. Include latency. Respond in spanish.
