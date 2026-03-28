---
name: bt-devices
description: Scan for nearby Bluetooth devices (speakers, TVs, headphones, phones). Triggers on keywords like "bluetooth", "parlante", "auriculares", "TV bluetooth", "dispositivos bluetooth", "BT", "nearby", "cercanos".
---

# Bluetooth Device Scanner

When the user asks about bluetooth devices, IMMEDIATELY execute this and format the output:

```bash
bash {baseDir}/scripts/bt-devices.sh scan
```

## Additional Commands

| Command | When to use |
|---|---|
| `list` | List registered known BT devices |
| `add MAC NAME` | Register a known BT device |
| `remove MAC` | Remove a known BT device |
| `last-seen` | Last detection per device |
| `history [hours]` | Presence ranges last N hours |

Examples:
```bash
bash {baseDir}/scripts/bt-devices.sh list
bash {baseDir}/scripts/bt-devices.sh add "AA:BB:CC:DD:EE:FF" "Parlante-Sala"
bash {baseDir}/scripts/bt-devices.sh last-seen
bash {baseDir}/scripts/bt-devices.sh history 12
```

Do NOT ask for confirmation on scan/list. Just run and show results.
Use blue circle for nearby, white circle for not detected. Scan takes ~10 seconds. Respond in spanish.
