# AI Hub Deployment Runbook

Use this for the current public-IP server setup.

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
Project:         /var/www/AI_salesman_plugin
Shared venv:     /Data/www/aikartvenv
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
- The shared host Python venv is `/Data/www/aikartvenv`. AI Hub runtime still runs inside Docker; the host venv is only for server-side helper commands.
- Public access comes through AI-KART's system Nginx, not Docker Nginx.
- `.env`, local data, caches, docs, and deploy backups are ignored runtime files.
- The pull step below stashes tracked server edits before pulling. It does not stash ignored runtime files.
- Do not run `git stash pop` as part of deployment. Stashes are only backups of server-local tracked edits.

## Deploy

Run one step at a time on the server. Do not paste the whole deploy as one giant block.

## SSH Session Safety

Long Docker builds can make SSH feel frozen or can drop the connection if the server is under CPU, RAM, or disk pressure. Run deployment inside `tmux` so the command keeps running even if your SSH session disconnects.

### Start Or Reattach Deploy Session

Run this before deploy steps:

```bash
tmux new -A -s aihub-deploy
```

If the connection drops, reconnect to the server and run the same command again:

```bash
tmux new -A -s aihub-deploy
```

### Optional SSH Keepalive

From your local machine, connect with keepalive enabled:

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 ev@143.198.5.97
```

### Why A Session May Close

- `set -e` stops the current shell when a command fails.
- Docker build/restart can spike CPU, memory, and disk I/O.
- A long command with little output can be treated as idle by SSH or a network hop.
- Pasting a large multi-line block makes it harder to see which line failed.

Keep using the numbered chunks below. For build and restart steps, stay inside `tmux`.

### 1. Fix Permissions

This restores the ownership and executable bits used by the stable server deploy.

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== fix project permissions =="
sudo chown -R "$(whoami):$(whoami)" /var/www/AI_salesman_plugin
chmod +x /var/www/AI_salesman_plugin/docker/entrypoint.sh
mkdir -p /var/www/AI_salesman_plugin/data
mkdir -p /var/www/AI_salesman_plugin/deploy/certs
sudo chown -R "$(whoami):$(whoami)" /var/www/AI_salesman_plugin/data /var/www/AI_salesman_plugin/deploy/certs
echo "Project permissions OK."
```

### 2. Pull Latest Code

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== safe git pull =="
git fetch origin
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash push -m "pre-aihub-deploy-$(date +%Y%m%d-%H%M%S)"
fi
git pull --ff-only
git status --short
```

### 3. Shared Host Python Venv

This is the same shared helper venv setup used by the stable server deploy. AI Hub runtime still runs inside Docker.

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== shared host python venv =="
sudo mkdir -p /Data/www
sudo chown "$(whoami):$(whoami)" /Data/www
if [ ! -x /Data/www/aikartvenv/bin/python ]; then
  python3 -m venv /Data/www/aikartvenv
fi
if [ -e /Data/www/aikartvenv ] && [ "$(stat -c '%u' /Data/www/aikartvenv)" != "$(id -u)" ]; then
  sudo chown -R "$(whoami):$(whoami)" /Data/www/aikartvenv
fi
. /Data/www/aikartvenv/bin/activate
which python
python -m pip install --upgrade pip
echo "Shared helper venv OK."
```

### 4. Create `.env` If Missing

If this creates `.env`, stop after this step, fill the secrets, then continue with step 5.

```bash
set -e
cd /var/www/AI_salesman_plugin

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
  echo "Created /var/www/AI_salesman_plugin/.env."
  echo "Fill OPENAI_API_KEY, GROQ_API_KEY, CRM_ADMIN_TOKEN, CLIENT_PANEL_DEFAULT_PASSWORD, and CLIENT_PANEL_TOKEN_SECRET before continuing."
else
  echo ".env already exists."
fi
```

Generate strong secret values with:

```bash
openssl rand -base64 32
```

### 5. Validate Security Environment

This must pass before build/restart.

```bash
set -e
cd /var/www/AI_salesman_plugin

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
  echo "Generate strong values, update .env, then rerun this validation step."
  echo "Example token generator: openssl rand -base64 32"
  exit 1
fi
echo "Security env OK."
```

### 6. Compose Sanity Check

This verifies AI Hub is still only `app` and `db`, with no Docker Nginx.

```bash
set -e
cd /var/www/AI_salesman_plugin

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
echo "Compose sanity OK."
```

### 7. Build App Image

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== build app image =="
sudo docker compose build --no-cache app
```

### 8. Restart AI Hub Services

```bash
set -e
cd /var/www/AI_salesman_plugin

echo "== restart db and app =="
sudo docker compose up -d --force-recreate db app
sudo docker compose ps
```

### 9. Local Smoke

This checks the local container route and verifies CRM admin API auth works with `CRM_ADMIN_TOKEN`.

```bash
set -e
cd /var/www/AI_salesman_plugin

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

## Docker Space Recovery

Use this only when Docker build or restart fails because disk space is exhausted. Run one chunk at a time and read the output.

### 1. Inspect Docker Disk Usage

```bash
cd /var/www/AI_salesman_plugin
sudo docker system df
```

### 2. Clear Docker Build Cache

This is usually the safest first cleanup when builds fail for space.

```bash
cd /var/www/AI_salesman_plugin
sudo docker builder prune -af
sudo docker system df
```

### 3. Remove Unused Images, Containers, And Networks

This removes unused Docker objects. It does not remove named volumes.

```bash
cd /var/www/AI_salesman_plugin
sudo docker system prune -af
sudo docker system df
```

### 4. Do Not Remove Volumes During Normal Deploy

Do not run this during normal deployment:

```bash
sudo docker system prune --volumes
```

Docker volumes can contain database data. Only use volume cleanup when the database has been backed up and the volumes are intentionally disposable.

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

The pull step already handles the old `docker-compose.yml` and `docker/entrypoint.sh` pull blockers by stashing tracked server edits before `git pull --ff-only`.

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
