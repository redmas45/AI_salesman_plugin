#!/bin/sh
set -eu

hub_origin="${PUBLIC_API_URL:-http://143.198.5.97/aihub}"
site_id="${CURRENT_SITE_ID:-ai_kart}"

printf '\n'
printf '============================================================\n'
printf ' AI Hub Docker is booting\n'
printf ' CRM:    %s/crm\n' "$hub_origin"
printf ' Widget: %s/shopbot.js?site=%s\n' "$hub_origin" "$site_id"
printf ' API:    http://localhost:8585\n'
printf '============================================================\n'
printf '\n'

exec "$@"
