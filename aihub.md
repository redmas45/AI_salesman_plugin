# AI Hub Deployment Runbook

Use this for the current public server setup before DNS is ready.

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
Project:         /var/www/AI_salesman_plugin
```

Public routing is owned by the shared system Nginx config from `Vercel_website/aikart.md`:

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

Do not run host-side `python` commands for file edits in this guide. Ubuntu may only have `python3`. The only `python` command below runs inside the AI Hub Docker container.

## What This Deploy Includes

- Public path-routed AI Hub at `/aihub/`, served by shared system Nginx.
- CRM light/dark readability fixes.
- Client remove action from Clients and Client detail.
- Settings save behavior fixes plus expanded `.env` model, voice, RAG, crawler, CRM, and Client Panel keys.
- Client detail pages split into tabs: Overview, Readiness, Catalog, Crawl, Activity, and Controls.
- Readiness and crawl reports shown as readable cards instead of raw cramped JSON.
- Catalog preview moved into a spacious review tab with images, filters, and pagination.
- Analytics upgraded with action/error rate, tokens per turn, status mix, transport mix, latency buckets, site mix, peak day, and recent events.
- Robustness work for readiness scanning, priority crawl reports, variants, adapter recognition, and crawler report storage.

## 1. Preflight

Run on the server:

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

If `git status --short` shows local changes on the server, inspect them before pulling.

## 2. Pull Code

```bash
cd /var/www/AI_salesman_plugin
git pull
```

## 3. Create Or Update `.env`

Use this server shape. Replace only secret placeholder values.

```bash
cat > /var/www/AI_salesman_plugin/.env <<'EOF'
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_API_URL=http://143.198.5.97/aihub
VOICE_ORB_API_URL=http://143.198.5.97/aihub
PUBLIC_STOREFRONT_ORIGIN=http://143.198.5.97

CURRENT_SITE_ID=ai_kart
DEFAULT_SITE_ID=ai_kart
AI_DEFAULT_SITE_ID=ai_kart

DEPLOYMENT_MODE=public-ip
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
LLM_TEMPERATURE=0.30
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=10
RAG_TOP_N=3
LLM_EXTRACTOR_ENABLED=false

OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
CRM_ADMIN_TOKEN=choose_strong_admin_token
CLIENT_PANEL_DEFAULT_PASSWORD=choose_client_panel_password
CLIENT_PANEL_TOKEN_SECRET=choose_client_panel_token_secret
EOF

nano /var/www/AI_salesman_plugin/.env
```

Keep these values for the current no-DNS deployment:

```text
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_STOREFRONT_ORIGIN=http://143.198.5.97
CLIENT_STORE_URL=http://143.198.5.97/
CURRENT_URL=http://143.198.5.97/
DEPLOYMENT_MODE=public-ip
```

Do not put AI-KART website admin credentials in this file. AI-KART admin credentials belong in `/var/www/Vercel_website/backend/.env`.

## 4. Verify Docker Compose

AI Hub must bind only to local port `5176`. Public access comes from shared system Nginx.

```bash
cd /var/www/AI_salesman_plugin

grep -n '127.0.0.1:5176:8585' docker-compose.yml
if grep -q '^  nginx:' docker-compose.yml; then
  echo "ERROR: docker-compose.yml still contains Docker nginx"
  exit 1
fi

sudo docker compose config --services | grep -E '^(db|app)$'
```

Expected:

```text
app and db services listed
```

## 5. Build And Start AI Hub

Use a fresh app image. Do not use only `docker compose restart` after CRM, analytics, crawler, settings, widget, or API changes.

If the build fails with `no space left on device`, run:

```bash
sudo docker system df
sudo docker builder prune -af
sudo docker system prune -af
```

Do not run `docker system prune --volumes` unless database volumes have been backed up and you intentionally want to remove unused Docker volumes.

Build and start:

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

## 6. Test Local AI Hub

Test the app before touching public Nginx.

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

If this fails, stop and inspect:

```bash
sudo docker compose logs --tail=160 app
sudo docker compose ps
```

## 7. Public Routing

AI Hub does not own public Nginx in this same-IP setup. Public `/aihub/` routing is configured from:

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

If local `http://127.0.0.1:5176/health` is `200` but public `/aihub/health` is not `200`, fix shared Nginx from `Vercel_website/aikart.md`.

## 8. Create Or Update AI-KART Client

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
Deploy mode: public-ip
Adapter: ai_kart_adapter.js
```

The Clients table has crawl, enable/disable, and remove actions. Remove is a soft delete of the CRM client record; tenant catalog data is not dropped.

## 9. Crawl AI-KART

Run after AI-KART is publicly reachable:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/', max_pages=1024, max_depth=100, site_id='ai_kart', reconcile_missing=True, source_name='crm_crawler')"
```

Then test one text turn:

```bash
curl -s -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart"}'
```

## 10. Final CRM Smoke

Open:

```text
http://143.198.5.97/aihub/crm/
```

Check:

- Light/dark toggle keeps text readable.
- Clients table has crawl, enable/disable, and remove actions.
- Client detail uses tabs instead of one cramped page.
- Readiness and crawl reports are readable cards, not raw JSON strips.
- Catalog review shows product images and allows searching/filtering.
- Settings shows `LLM_MODEL`, `LLM_TEMPERATURE`, `GROQ_TTS_MODEL`, `EMBEDDING_MODEL`, crawler settings, and client-panel secrets.
- Analytics shows KPI cards, demand trend, operations, product demand, intent mix, transport/status/latency breakdowns, and recent events.

## 11. Common Failure Map

```text
python: command not found
  -> This guide does not use host-side python. Use the shell commands exactly as written.

127.0.0.1:5176/health fails
  -> AI Hub app is not running correctly. Check docker compose logs app.

127.0.0.1:5176 works but /aihub/health fails publicly
  -> Shared system Nginx route is missing or stale. Apply Vercel_website/aikart.md.

CRM still shows old browser token prompt
  -> Old image or browser cache. Rebuild app with --no-cache, then hard refresh.

Client Panel has a plain old UI
  -> Rebuild client_panel with npm run build and restart PM2.

Mic does not work on public HTTP
  -> Browser microphone access requires HTTPS on public origins. Use DNS + HTTPS when ready.
```
