#!/usr/bin/env bash
# bt-devices.sh — Bluetooth device scanner for OpenClaw
# Runs inside the container, calls ping-server.py on the host
# Usage: bt-devices.sh <command> [args]

set -euo pipefail

PING_SERVER="http://192.168.1.54:8888"

fetch() {
  local url="$1"
  local timeout="${2:-10}"
  result=$(curl -s --connect-timeout 5 --max-time "$timeout" "$url" 2>&1)
  if [ $? -ne 0 ] || [ -z "$result" ]; then
    echo '{"error":"ping-server no responde. Verificar que el servicio este corriendo en el host."}'
    exit 1
  fi
  echo "$result"
}

case "${1:-help}" in

  scan)
    fetch "${PING_SERVER}/bt-scan" 25
    ;;

  list)
    fetch "${PING_SERVER}/bt-devices" 5
    ;;

  add)
    mac="${2:-}"
    name="${3:-}"
    if [ -z "$mac" ] || [ -z "$name" ]; then
      echo '{"error":"uso: bt-devices.sh add MAC NOMBRE"}'
      exit 1
    fi
    result=$(curl -s --connect-timeout 5 --max-time 5 \
      -X POST "${PING_SERVER}/bt-devices" \
      -H "Content-Type: application/json" \
      -d "{\"action\":\"add\",\"mac\":\"${mac}\",\"name\":\"${name}\"}" 2>&1)
    echo "$result"
    ;;

  remove)
    mac="${2:-}"
    if [ -z "$mac" ]; then
      echo '{"error":"uso: bt-devices.sh remove MAC"}'
      exit 1
    fi
    result=$(curl -s --connect-timeout 5 --max-time 5 \
      -X POST "${PING_SERVER}/bt-devices" \
      -H "Content-Type: application/json" \
      -d "{\"action\":\"remove\",\"mac\":\"${mac}\"}" 2>&1)
    echo "$result"
    ;;

  last-seen)
    fetch "${PING_SERVER}/logs/last-seen" 5
    ;;

  history)
    hours="${2:-24}"
    fetch "${PING_SERVER}/logs/presence?hours=${hours}" 5
    ;;

  help|*)
    cat << 'EOF'
bt-devices.sh — Bluetooth device scanner

Commands:
  scan              Discover nearby BT devices + check known (~10s)
  list              List registered known devices
  add MAC NAME      Register a known BT device
  remove MAC        Remove a known BT device
  last-seen         Last detection per device
  history [N]       Presence ranges last N hours (default 24)

Examples:
  bt-devices.sh scan
  bt-devices.sh list
  bt-devices.sh add "AA:BB:CC:DD:EE:FF" "Parlante-Sala"
  bt-devices.sh remove "AA:BB:CC:DD:EE:FF"
  bt-devices.sh last-seen
  bt-devices.sh history 12
EOF
    ;;
esac
