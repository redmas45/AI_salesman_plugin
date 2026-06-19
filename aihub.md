# AI Hub Deployment Runbook

Use this for the current public-IP server setup.

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
Project:         /var/www/AI_salesman_plugin
```

Public routing is owned by the shared Nginx config in `/var/www/Vercel_website/aikart.md`:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

## Rules

- AI Hub runs only Docker Compose `db` and `app`.
- Public access comes through AI-KART's system Nginx, not Docker Nginx.
- `.env`, local data, caches, docs, and deploy backups are ignored runtime files.
- The deploy command below stashes tracked server edits before pulling. It does not stash ignored runtime files.
- Do not run `git stash pop` as part of deployment. Stashes are only backups of server-local tracked edits.

## Deploy

Paste this on the server. It is safe to rerun.

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== safe git pull =="
git fetch origin
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash push -m "pre-aihub-deploy-$(date +%Y%m%d-%H%M%S)"
fi
git pull --ff-only

echo "== ensure .env exists =="
if [ ! -f .env ]; then
  cat > .env <<'EOF'
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_API_URL=http://143.198.5.97/aihub
VOICE_ORB_API_URL=http://143.198.5.97/aihub
PUBLIC_STOREFRONT_ORIGIN=http://143.198.5.97
CORS_ORIGINS=http://143.198.5.97

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
CRM_ADMIN_TOKEN=replace-with-long-random-admin-token-min-12-chars
CLIENT_PANEL_DEFAULT_PASSWORD=replace-with-strong-client-panel-password
CLIENT_PANEL_TOKEN_SECRET=replace-with-long-random-client-panel-signing-secret
EOF
  echo "Created /var/www/AI_salesman_plugin/.env. Fill the secrets, then rerun this deploy block."
  exit 1
fi

echo "== validate required security env =="
missing=0
require_secret() {
  key="$1"
  min_len="$2"
  value="$(grep -E "^${key}=" .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
  if [ -z "$value" ] || echo "$value" | grep -Eq '^(choose_|replace-|your_|change-this|client123)'; then
    echo "ERROR: $key must be set to a real secret in /var/www/AI_salesman_plugin/.env"
    missing=1
    return
  fi
  if [ "${#value}" -lt "$min_len" ]; then
    echo "ERROR: $key must be at least $min_len characters."
    missing=1
  fi
}

require_secret CRM_ADMIN_TOKEN 12
require_secret CLIENT_PANEL_DEFAULT_PASSWORD 12
require_secret CLIENT_PANEL_TOKEN_SECRET 16

CORS_VALUE="$(grep -E '^CORS_ORIGINS=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ -z "$CORS_VALUE" ] || [ "$CORS_VALUE" = "*" ]; then
  echo "ERROR: CORS_ORIGINS must be explicit, for example: CORS_ORIGINS=http://143.198.5.97"
  missing=1
fi

if [ "$missing" -ne 0 ]; then
  echo "Generate strong values, update .env, then rerun this deploy block."
  echo "Example token generator: openssl rand -base64 32"
  exit 1
fi

echo "== compose sanity =="
grep -q '127.0.0.1:5176:8585' docker-compose.yml
if grep -q '^  nginx:' docker-compose.yml; then
  echo "ERROR: docker-compose.yml must not contain a Docker nginx service."
  exit 1
fi
SERVICES="$(sudo docker compose config --services | sort | tr '\n' ' ')"
if [ "$SERVICES" != "app db " ]; then
  echo "ERROR: expected compose services 'app db', got: $SERVICES"
  exit 1
fi

echo "== build and restart =="
sudo docker compose build --no-cache app
sudo docker compose up -d --force-recreate db app
sudo docker compose ps

echo "== local smoke =="
curl -fsS http://127.0.0.1:5176/health >/dev/null
curl -fsS http://127.0.0.1:5176/crm/ | grep -E 'assets/index-.*\.js' >/dev/null
CRM_ADMIN_TOKEN_VALUE="$(grep -E '^CRM_ADMIN_TOKEN=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
curl -fsS http://127.0.0.1:5176/v1/admin/overview \
  -H "x-crm-admin-token: ${CRM_ADMIN_TOKEN_VALUE}" >/dev/null
echo "AI Hub local deploy OK."
```

## Public Smoke

Run after AI-KART's shared Nginx route has been applied.

```bash
curl -fsS http://143.198.5.97/aihub/health >/dev/null
curl -fsS http://143.198.5.97/aihub/crm/ | grep -E 'assets/index-.*\.js' >/dev/null
echo "AI Hub public route OK."
```

If local `127.0.0.1:5176` works but public `/aihub/` fails, apply `/var/www/Vercel_website/aikart.md`.

## Crawl AI-KART

Run this after AI-KART is public and the `ai_kart` client exists in CRM.
This `python` runs inside the AI Hub Docker container.

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/', max_pages=1024, max_depth=100, site_id='ai_kart', reconcile_missing=True, source_name='crm_crawler')"

curl -fsS -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart"}'
```

## Git Recovery

The deploy command already handles the old `docker-compose.yml` and `docker/entrypoint.sh` pull blockers by stashing tracked server edits before `git pull --ff-only`.

Useful inspection commands:

```bash
cd /var/www/AI_salesman_plugin
git status --short
git stash list --grep=pre-aihub-deploy
```

If `git pull --ff-only` says the branch has diverged, the server has local commits. Do not force reset from a deploy paste. Inspect with:

```bash
git log --oneline --left-right HEAD...@{u}
```

## Ownership

- AI Hub settings and secrets live in `/var/www/AI_salesman_plugin/.env`.
- AI-KART admin credentials do not belong in AI Hub. They live in `/var/www/Vercel_website/backend/.env`.
- Deploy order is AI Hub, AI-KART/shared Nginx, then Client Panel.
