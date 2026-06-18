# AI Hub Deployment Runbook

Use this for the current no-DNS server setup.

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
Project:         /var/www/AI_salesman_plugin
```

Public routing is owned by AI-KART Nginx config:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

Deploy order:

1. Deploy AI Hub with this file.
2. Deploy or reload AI-KART Nginx from `/var/www/Vercel_website/aikart.md`.
3. Deploy Client Panel from `/var/www/client_panel/clientpanel.md`.

Do not use host-side `python` in this guide. Ubuntu may only have `python3`.

## What This Deploy Includes

- CRM light/dark theme readability fix.
- Remove-client action in the Clients table and Client detail page.
- Expanded Settings page for model, voice, RAG, crawler, deployment, CRM, and Client Panel `.env` keys.
- Analytics API fields: `action_rate`, `error_rate`, `tokens_per_turn`, `status_mix`, `transport_mix`, `latency_buckets`, `site_mix`, `peak_day`, and `recent_events`.
- Richer CRM Analytics UI.

## 1. Preflight

Run this on the server:

```bash
set -e

cd /var/www/AI_salesman_plugin

command -v git
command -v sed
command -v sudo
sudo docker compose version

pwd
git status --short
```

Expected:

```text
/var/www/AI_salesman_plugin
docker compose version output
```

If `git status --short` shows local changes on the server, stop and inspect them before pulling.

## 2. Pull Code

```bash
cd /var/www/AI_salesman_plugin
git pull
```

## 3. Create Or Update `.env`

Use this full server `.env` shape. Replace only the secret placeholder values.

```bash
cat > /var/www/AI_salesman_plugin/.env <<'EOF'
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_API_URL=http://143.198.5.97/aihub
VOICE_ORB_API_URL=http://143.198.5.97/aihub

CURRENT_SITE_ID=ai_kart
DEFAULT_SITE_ID=ai_kart
AI_DEFAULT_SITE_ID=ai_kart

CLIENT_STORE_URL=http://143.198.5.97/
CURRENT_URL=http://143.198.5.97/

CRAWL_ON_STARTUP=true
CRAWL_PERIODIC_ENABLED=true
CRAWL_MAX_PAGES=1024
CRAWL_MAX_DEPTH=100

STT_PROVIDER=groq
GROQ_STT_MODEL=whisper-large-v3-turbo
TTS_PROVIDER=groq
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=troy
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=10
RAG_TOP_N=3

OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
CRM_ADMIN_TOKEN=choose_strong_token
CLIENT_PANEL_DEFAULT_PASSWORD=client_pass_1
CLIENT_PANEL_TOKEN_SECRET=client_token_1
EOF

nano /var/www/AI_salesman_plugin/.env
```

Replace:

```text
your_openai_key
your_groq_key
choose_strong_token
choose_client_panel_password
choose_client_panel_token_secret
```

Keep these as shown for the current path-routed public IP setup:

```text
HUB_PUBLIC_URL=http://143.198.5.97/aihub
CLIENT_STORE_URL=http://143.198.5.97/
CURRENT_URL=http://143.198.5.97/
```

## 4. Configure Docker App Port

The AI Hub app must bind only to local port `5176`. System Nginx exposes it publicly under `/aihub/`.

Run this exact idempotent block:

```bash
cd /var/www/AI_salesman_plugin

if grep -q '      - "8585:8585"' docker-compose.yml; then
  sed -i 's#      - "8585:8585"#      - "127.0.0.1:5176:8585"#' docker-compose.yml
fi

if ! grep -q '127.0.0.1:5176:8585' docker-compose.yml; then
  echo "ERROR: docker-compose.yml does not expose app on 127.0.0.1:5176"
  grep -n '8585' docker-compose.yml || true
  exit 1
fi

grep -n '5176:8585' docker-compose.yml
```

Expected:

```text
127.0.0.1:5176:8585
```

## 5. Disable Docker Nginx For This Server

This setup uses system Nginx from the AI-KART guide, not the Docker Nginx service.

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose stop nginx || true
sudo docker compose rm -f nginx || true
```

It is fine if this says the container was stopped or removed.

## 6. Build And Start AI Hub

Use a fresh app image. Do not use only `docker compose restart` after CRM, analytics, crawler, settings, widget, or API changes.

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose build --no-cache app
sudo docker compose up -d --force-recreate db app
sudo docker compose ps
```

Expected:

```text
db   running/healthy
app  running
```

## 7. Test Local AI Hub

Load the admin token from `.env` and test the local app before touching public Nginx.

```bash
cd /var/www/AI_salesman_plugin
set -a
. ./.env
set +a

curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5176/health
curl -s http://127.0.0.1:5176/crm/ | grep -E 'assets/index-.*\.js'
curl -s http://127.0.0.1:5176/crm/app.js | grep 'crm_reload'
curl -s http://127.0.0.1:5176/crm/app.js | grep -q 'prompt(' \
  && echo "ERROR: old CRM app.js still served" \
  || echo "OK: no old prompt app.js"
curl -s "http://127.0.0.1:5176/v1/admin/analytics?range=7d" \
  -H "x-crm-admin-token: ${CRM_ADMIN_TOKEN}" \
  | grep -E '"latency_buckets"|"transport_mix"|"action_rate"'
curl -s "http://127.0.0.1:5176/v1/admin/settings" \
  -H "x-crm-admin-token: ${CRM_ADMIN_TOKEN}" \
  | grep -E '"LLM_MODEL"|"GROQ_TTS_MODEL"|"EMBEDDING_MODEL"'
```

Expected:

```text
200
current CRM asset path
legacy reload shim
OK: no old prompt app.js
analytics fields present
settings fields present
```

If this fails, do not continue to public routing. Check:

```bash
sudo docker compose logs --tail=120 app
sudo docker compose ps
```

## 8. Public Routing

AI Hub does not own public Nginx in this same-IP setup. Public `/aihub/` is configured from:

```text
/var/www/Vercel_website/aikart.md
```

After AI-KART/shared Nginx is applied, test public Hub routes:

```bash
cd /var/www/AI_salesman_plugin
set -a
. ./.env
set +a

curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aihub/health
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aihub/crm/
curl -s http://143.198.5.97/aihub/crm/ | grep -E 'assets/index-.*\.js'
curl -s http://143.198.5.97/aihub/crm/app.js | grep 'crm_reload'
curl -s http://143.198.5.97/aihub/crm/app.js | grep -q 'prompt(' \
  && echo "ERROR: old public CRM app.js still served" \
  || echo "OK: no old public prompt app.js"
curl -s "http://143.198.5.97/aihub/v1/admin/analytics?range=7d" \
  -H "x-crm-admin-token: ${CRM_ADMIN_TOKEN}" \
  | grep -E '"latency_buckets"|"transport_mix"|"action_rate"'
```

Expected:

```text
200
200
current CRM asset path
legacy reload shim
OK: no old public prompt app.js
analytics fields present
```

If local `http://127.0.0.1:5176/health` is `200` but public `/aihub/health` is not `200`, the fix belongs in the AI-KART Nginx guide, not in this repo.

## 9. Create Or Update AI-KART Client

Open:

```text
http://143.198.5.97/aihub/crm/
```

Use `CRM_ADMIN_TOKEN` from `.env`.

Client values:

```text
Site ID: ai_kart
Website URL: http://143.198.5.97/
Enabled: yes
```

The Clients table has crawl, enable/disable, and remove actions. Remove is a soft delete of the CRM client record; tenant catalog data is not dropped.

## 10. Crawl AI-KART

Run after AI-KART is publicly reachable:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/', max_pages=1024, max_depth=100, site_id='ai_kart', reconcile_missing=True, source_name='crm_crawler')"
```

Then test a text turn:

```bash
curl -s -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart"}'
```

## 11. Final CRM Smoke

Open:

```text
http://143.198.5.97/aihub/crm/
```

Check:

- Light/dark toggle keeps the top header readable.
- Clients table has crawl, enable/disable, and remove actions.
- Settings shows `LLM_MODEL`, `GROQ_TTS_MODEL`, `EMBEDDING_MODEL`, crawler settings, and client-panel secrets.
- Analytics shows KPI cards, demand trend, operations pulse, product demand, intent mix, transport/status/latency breakdowns, and recent events.

## 12. Common Failure Map

```text
python: command not found
  -> This guide does not use host-side python. Use the sed block in step 4.

127.0.0.1:5176/health fails
  -> AI Hub app is not running correctly. Check docker compose logs app.

127.0.0.1:5176 works but /aihub/health fails publicly
  -> Shared system Nginx route is missing or stale. Apply Vercel_website/aikart.md.

CRM still shows old browser token prompt
  -> Old CRM image or browser cache. Rebuild app with --no-cache, then hard refresh.

Client Panel has a plain old UI
  -> Rebuild client_panel with npm run build and restart PM2.
```
