#!/bin/bash
echo "=== Pi 5 Health Check ==="
echo "CPU Temp:  $(vcgencmd measure_temp)"
echo "Throttle:  $(vcgencmd get_throttled)"
echo "Voltage:   $(vcgencmd measure_volts core)"
echo "NVMe Temp: $(sudo nvme smart-log /dev/nvme0 2>/dev/null | grep 'temperature' | head -1)"
echo "Uptime:    $(uptime -p)"
echo "Disk:      $(df -h / | tail -1)"
