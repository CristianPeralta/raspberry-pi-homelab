---
name: adguard-home
description: Control AdGuard Home DNS server via API. Triggers on keywords like red, internet, bloquear, desbloquear, dispositivos, DNS, AdGuard, control parental, noche, horario, wifi, paginas, apps.
---

# AdGuard Home Control

Manage the home network DNS server (AdGuard Home) running on this Raspberry Pi.

## Script

```bash
bash {baseDir}/scripts/adguard-ctl.sh <command> [args]
```

Run with `help` for the full command list.

## Common Tasks

### Ver estado
```bash
bash {baseDir}/scripts/adguard-ctl.sh status
```

### Ver dispositivos
```bash
bash {baseDir}/scripts/adguard-ctl.sh clients
```

### Bloquear un sitio
```bash
bash {baseDir}/scripts/adguard-ctl.sh rule-add "||dominio.com^"
```

### Desbloquear un sitio
```bash
bash {baseDir}/scripts/adguard-ctl.sh rule-remove "||dominio.com^"
```

### Registrar nuevo dispositivo
```bash
bash {baseDir}/scripts/adguard-ctl.sh client-add '{"name":"NOMBRE","ids":["IP"],"tags":["device_phone","user_regular"],"use_global_settings":true,"use_global_blocked_services":true}'
```

### Activar/desactivar proteccion
```bash
bash {baseDir}/scripts/adguard-ctl.sh protection-on
bash {baseDir}/scripts/adguard-ctl.sh protection-off
```

### Ultimas consultas DNS
```bash
bash {baseDir}/scripts/adguard-ctl.sh querylog 20
```

### Bloquear servicios con horario
Schedule: milisegundos desde medianoche. 22:00=79200000, 06:00=21600000, 08:00=28800000.
```bash
bash {baseDir}/scripts/adguard-ctl.sh block-service-global '{"ids":["tiktok","instagram"],"schedule":{"time_zone":"America/Lima","mon":{"start":79200000,"end":28800000}}}'
```

Services: tiktok, instagram, snapchat, facebook, twitter, youtube, twitch, netflix, reddit, whatsapp, telegram, discord, spotify, steam, epicgames, minecraft, roblox.

## Response Format (Telegram)

- Responder en espanol
- Mensajes cortos y claros
- Listas con bullets, NO tablas
- Confirmar acciones con mensaje breve

## Dispositivos del Hogar

- PC-Cristian: 192.168.1.37 (WiFi), .38 (Ethernet)
- Celular-Cristian: 192.168.1.40
- Celular-Roxsy: 192.168.1.43
- Router-Movistar: 192.168.1.1
- Raspberry-Pi: 192.168.1.54

## Red

- Timezone: America/Lima (UTC-5)
