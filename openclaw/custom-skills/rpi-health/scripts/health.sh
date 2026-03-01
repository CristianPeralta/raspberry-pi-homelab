#!/bin/bash
# RPi Health Check - no bc dependency, uses awk for math
set -euo pipefail

cmd="${1:-status}"

get_temp() {
  raw=$(cat /sys/class/thermal/thermal_zone0/temp)
  temp=$(awk "BEGIN {printf \"%.1f\", $raw / 1000}")
  if (( raw > 80000 )); then badge="CRITICAL";
  elif (( raw > 70000 )); then badge="WARNING";
  elif (( raw > 60000 )); then badge="WARM";
  else badge="OK"; fi
  echo "${temp}°C [${badge}]"
}

get_mem() {
  awk '/MemTotal/ {total=$2} /MemAvailable/ {avail=$2} END {
    used=(total-avail)/1048576; t=total/1048576; pct=int(used*100/t)
    printf "%.1fG / %.1fG (%d%%)\n", used, t, pct
  }' /proc/meminfo
}

get_uptime() {
  raw=$(awk '{print int($1)}' /proc/uptime)
  days=$((raw / 86400))
  hours=$(( (raw % 86400) / 3600 ))
  mins=$(( (raw % 3600) / 60 ))
  echo "${days}d ${hours}h ${mins}m"
}

get_disk() {
  df -h / | awk 'NR==2 {printf "%s / %s (%s)\n", $3, $2, $5}'
}

get_load() {
  read one five fifteen rest < /proc/loadavg
  echo "$one / $five / $fifteen"
}

case "$cmd" in
  temp|temperature)
    echo "CPU Temperature: $(get_temp)"
    ;;
  mem|memory)
    echo "RAM: $(get_mem)"
    ;;
  disk)
    echo "Disk: $(get_disk)"
    ;;
  uptime)
    echo "Uptime: $(get_uptime)"
    ;;
  load)
    cores=$(nproc)
    echo "Load: $(get_load) (${cores} cores)"
    ;;
  status|health)
    echo "=== Raspberry Pi 5 Health ==="
    echo ""
    echo "Temp: $(get_temp)"
    echo "Uptime: $(get_uptime)"
    echo "Load: $(get_load)"
    echo "RAM: $(get_mem)"
    echo "Disk: $(get_disk)"
    ;;
  help)
    echo "Commands: status, temp, mem, disk, uptime, load, help"
    ;;
  *)
    echo "Unknown: $cmd. Run 'health.sh help'"
    exit 1
    ;;
esac
