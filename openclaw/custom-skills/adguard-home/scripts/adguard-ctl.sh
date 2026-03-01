#!/usr/bin/env bash
# adguard-ctl.sh — AdGuard Home CLI wrapper for OpenClaw
# Usage: adguard-ctl.sh <command> [args]

set -euo pipefail

ADGUARD_HOST="${ADGUARD_HOST:-192.168.1.54}"
ADGUARD_PORT="${ADGUARD_PORT:-80}"
ADGUARD_USER="${ADGUARD_USER:-admin}"
ADGUARD_PASS="${ADGUARD_PASS:-changeme}"
BASE_URL="http://${ADGUARD_HOST}:${ADGUARD_PORT}"

api() {
  local method="$1" endpoint="$2"
  shift 2
  curl -s -u "${ADGUARD_USER}:${ADGUARD_PASS}" \
    -X "$method" \
    -H "Content-Type: application/json" \
    "${BASE_URL}/control${endpoint}" "$@"
}

case "${1:-help}" in

  status)
    api GET /status
    ;;

  stats)
    api GET /stats
    ;;

  # --- Protection toggle ---
  protection-on)
    api POST /dns_config '{"protection_enabled":true}'
    echo '{"result":"protection enabled"}'
    ;;

  protection-off)
    api POST /dns_config '{"protection_enabled":false}'
    echo '{"result":"protection disabled"}'
    ;;

  # --- Query log ---
  querylog)
    limit="${2:-20}"
    api GET "/querylog?limit=${limit}"
    ;;

  # --- Clients ---
  clients)
    api GET /clients
    ;;

  client-add)
    # Usage: adguard-ctl.sh client-add '{"name":"Phone","ids":["192.168.1.40"],"tags":["device_phone"],"use_global_settings":true,"use_global_blocked_services":true}'
    api POST /clients/add -d "$2"
    ;;

  client-update)
    # Usage: adguard-ctl.sh client-update '{"name":"Phone","data":{...}}'
    api POST /clients/update -d "$2"
    ;;

  client-delete)
    # Usage: adguard-ctl.sh client-delete "Phone"
    api POST /clients/delete -d "{\"name\":\"$2\"}"
    ;;

  # --- Blocked services (per-client or global) ---
  blocked-services)
    api GET /blocked_services/all
    ;;

  block-service-global)
    # Usage: adguard-ctl.sh block-service-global '{"ids":["tiktok","instagram"],"schedule":{"time_zone":"America/Lima"}}'
    api PUT /blocked_services/update -d "$2"
    ;;

  # --- Filtering ---
  filtering-status)
    api GET /filtering/status
    ;;

  filtering-add)
    # Usage: adguard-ctl.sh filtering-add "https://example.com/list.txt" "List Name"
    api POST /filtering/add_url -d "{\"name\":\"$3\",\"url\":\"$2\",\"whitelist\":false}"
    ;;

  filtering-refresh)
    api POST /filtering/refresh -d '{"whitelist":false}'
    ;;

  # --- Custom filtering rules ---
  rules-get)
    api GET /filtering/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d.get('user_rules',[])))" 2>/dev/null || api GET /filtering/status
    ;;

  rule-add)
    # Usage: adguard-ctl.sh rule-add "||example.com^"
    # First get existing rules, then append
    existing=$(api GET /filtering/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d.get('user_rules',[])))" 2>/dev/null || echo "")
    new_rules="${existing}"$'\n'"$2"
    api POST /filtering/set_rules -d "{\"rules\":$(echo "$new_rules" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip().split('\n')))")}"
    echo '{"result":"rule added"}'
    ;;

  rule-remove)
    # Usage: adguard-ctl.sh rule-remove "||example.com^"
    existing=$(api GET /filtering/status | python3 -c "import sys,json; d=json.load(sys.stdin); rules=[r for r in d.get('user_rules',[]) if r != sys.argv[1]]; print('\n'.join(rules))" "$2" 2>/dev/null || echo "")
    api POST /filtering/set_rules -d "{\"rules\":$(echo "$existing" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip().split('\n')))")}"
    echo '{"result":"rule removed"}'
    ;;

  # --- DNS config ---
  dns-config)
    api GET /dns_info
    ;;

  # --- DHCP ---
  dhcp-status)
    api GET /dhcp/status
    ;;

  # --- Network scan (requires arp-scan on host, run via SSH) ---
  scan)
    echo "Note: Network scan requires running on the host, not inside Docker."
    echo "Use: ssh cristian@192.168.1.54 'sudo arp-scan --localnet'"
    ;;

  # --- Top clients ---
  top)
    api GET /stats
    ;;

  help|*)
    cat << 'EOF'
adguard-ctl.sh — AdGuard Home control

Commands:
  status              Show AdGuard Home status
  stats               Show statistics (queries, blocked, top domains)
  top                 Same as stats (includes top clients/domains)

  protection-on       Enable DNS protection
  protection-off      Disable DNS protection

  clients             List all clients (registered + auto-detected)
  client-add JSON     Add a named client
  client-update JSON  Update a client
  client-delete NAME  Delete a client by name

  querylog [N]        Show last N DNS queries (default: 20)

  blocked-services        List all available services to block
  block-service-global JSON  Set globally blocked services + schedule

  filtering-status    Show filter lists and rules
  filtering-add URL NAME  Add a filter list
  filtering-refresh   Refresh all filter lists
  rules-get           Show custom user rules
  rule-add RULE       Add a custom blocking/allow rule
  rule-remove RULE    Remove a custom rule

  dns-config          Show DNS configuration
  dhcp-status         Show DHCP status
  scan                Network scan (instructions)

Examples:
  adguard-ctl.sh status
  adguard-ctl.sh clients
  adguard-ctl.sh rule-add "||tiktok.com^"
  adguard-ctl.sh rule-remove "||tiktok.com^"
  adguard-ctl.sh client-add '{"name":"Celular-Papa","ids":["192.168.1.40"],"tags":["device_phone","user_regular"],"use_global_settings":true,"use_global_blocked_services":true}'
  adguard-ctl.sh block-service-global '{"ids":["tiktok","snapchat"],"schedule":{"time_zone":"America/Lima","sun":{"start":79200000,"end":28800000},"mon":{"start":79200000,"end":28800000},"tue":{"start":79200000,"end":28800000},"wed":{"start":79200000,"end":28800000},"thu":{"start":79200000,"end":28800000},"fri":{"start":79200000,"end":28800000},"sat":{"start":79200000,"end":28800000}}}'
EOF
    ;;
esac
