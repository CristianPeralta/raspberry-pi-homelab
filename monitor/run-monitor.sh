#!/bin/bash
set -a
source /home/cristian/homelab/monitor/config.env
set +a
python3 /home/cristian/homelab/monitor/homelab-monitor.py
