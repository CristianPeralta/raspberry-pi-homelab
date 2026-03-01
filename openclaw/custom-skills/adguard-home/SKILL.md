---
name: adguard-home
description: Control AdGuard Home DNS server via API. Use when the user asks about network management, blocking/unblocking websites or apps, parental controls, viewing connected devices, DNS queries, ad blocking, checking network status, or night mode. Triggers on keywords like red, internet, bloquear, desbloquear, dispositivos, DNS, AdGuard, control parental, noche, horario, wifi, paginas, apps.
---

# AdGuard Home Control

Manage the home network DNS server (AdGuard Home) running on this Raspberry Pi.

## Script

All commands go through:

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

### Ver estadisticas
```bash
bash {baseDir}/scripts/adguard-ctl.sh stats
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

Tags: device_phone, device_pc, device_laptop, device_tablet, device_tv, device_camera, device_other, os_android, os_ios, os_linux, os_windows, user_admin, user_child, user_regular.

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

Services: tiktok, instagram, snapchat, facebook, twitter, youtube, twitch, netflix, reddit, whatsapp, telegram, discord, spotify, steam, epicgames, minecraft, roblox. Run `blocked-services` for full list.

### Ver reglas custom
```bash
bash {baseDir}/scripts/adguard-ctl.sh rules-get
```

## Response Format (Telegram)

- Responder en espanol
- Mensajes cortos y claros
- Listas con bullets, NO tablas
- Confirmar acciones con mensaje breve

## Dispositivos del Hogar

- PC-Cristian: 192.168.1.37 (WiFi), .38 (Ethernet) — PC Linux, owner
- Celular-Cristian: 192.168.1.40 — Phone Android, owner
- Celular-Roxsy: 192.168.1.43 — Phone Android, usuario regular
- Router-Movistar: 192.168.1.1
- Raspberry-Pi: 192.168.1.54, 127.0.0.1

## Personas
- Cristian: owner/admin
- Roxsy: usuario regular

## Red

- Router: 192.168.1.1 (MitraStar, Movistar Peru)
- DHCP: 192.168.1.33 - .96
- Timezone: America/Lima (UTC-5)
