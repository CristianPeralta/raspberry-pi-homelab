#!/usr/bin/env bash
# wifi-devices.sh — WiFi device scanner for OpenClaw
# Runs inside the container, calls ping-server.py on the host
# Usage: wifi-devices.sh <command> [args]

set -euo pipefail

PING_SERVER="http://192.168.1.54:8888"

fetch() {
  local url="$1"
  local timeout="${2:-10}"
  result=$(curl -s --connect-timeout 5 --max-time "$timeout" "$url" 2>&1)
  if [ $? -ne 0 ] || [ -z "$result" ]; then
    echo '{"error":"ping-server no responde en '"${PING_SERVER}"'. Verificar que el servicio este corriendo en el host."}'
    exit 1
  fi
  echo "$result"
}

case "${1:-help}" in

  active)
    minutes="${2:-0}"
    if [ "$minutes" -gt 0 ] 2>/dev/null; then
      fetch "${PING_SERVER}/scan?minutes=${minutes}"
    else
      fetch "${PING_SERVER}/scan"
    fi
    ;;

  devices)
    fetch "${PING_SERVER}/devices"
    ;;

  last-seen)
    fetch "${PING_SERVER}/logs/last-seen"
    ;;

  history)
    hours="${2:-24}"
    fetch "${PING_SERVER}/logs/presence?hours=${hours}"
    ;;

  add-device)
    json_data="${2:-}"
    if [ -z "$json_data" ]; then
      echo '{"error":"uso: wifi-devices.sh add-device \"{\\\"name\\\":\\\"...\\\",\\\"type\\\":\\\"...\\\",\\\"wifi_ip\\\":\\\"...\\\"}\"}"'
      exit 1
    fi
    result=$(curl -s --connect-timeout 5 --max-time 5 \
      -X POST "${PING_SERVER}/devices" \
      -H "Content-Type: application/json" \
      -d "$json_data" 2>&1)
    echo "$result"
    ;;

  help|*)
    cat << 'EOF'
wifi-devices.sh — WiFi device scanner

Commands:
  active          Scan all known devices, show online/offline
  active N        Same + DNS activity from last N minutes
  devices         List all registered devices
  last-seen       Last detection per device
  history [N]     Presence ranges last N hours (default 24)
  add-device JSON Add/update a device

Examples:
  wifi-devices.sh active
  wifi-devices.sh active 30
  wifi-devices.sh devices
  wifi-devices.sh last-seen
  wifi-devices.sh history 12
  wifi-devices.sh add-device '{"name":"TV-Sala","type":"tv","wifi_ip":"192.168.1.50"}'
EOF
    ;;
esac
