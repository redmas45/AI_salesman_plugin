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

The snippets below are written for an interactive SSH shell. They should print errors without closing your SSH session. Do not add `set -e` or `exit` while running them manually.

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

- `exit` closes the current SSH shell. Do not paste deploy checks that contain `exit`.
- `set -e` can make a manual deploy harder to debug because one failed check may stop the shell or tmux pane.
- Docker build/restart can spike CPU, memory, and disk I/O.
- A long command with little output can be treated as idle by SSH or a network hop.
- Pasting a large multi-line block makes it harder to see which line failed.

Keep using the numbered chunks below. For build and restart steps, stay inside `tmux`.

### 1. Fix Permissions

This restores the ownership and executable bits used by the stable server deploy.

```bash
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

Run these checks one by one. If a check prints `ERROR`, fix `.env`, rerun that one check, and continue only after every check prints `OK`.

#### 5.1 Check Current Folder

```bash
cd /var/www/AI_salesman_plugin
pwd
```

#### 5.2 Check `CORS_ORIGINS`

For the current public-IP deployment, this should be `http://143.198.5.97`.

```bash
CORS_VALUE="$(grep -E '^CORS_ORIGINS=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ "$CORS_VALUE" = "http://143.198.5.97" ]; then
  echo "CORS_ORIGINS OK."
else
  echo "ERROR: set CORS_ORIGINS=http://143.198.5.97 in /var/www/AI_salesman_plugin/.env"
  echo "Current CORS_ORIGINS=${CORS_VALUE:-missing}"
fi
```

To fix only this value:

```bash
grep -q '^CORS_ORIGINS=' .env \
  && sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=http://143.198.5.97|' .env \
  || echo 'CORS_ORIGINS=http://143.198.5.97' >> .env
grep -E '^CORS_ORIGINS=' .env
```

#### 5.3 Check `CRM_ADMIN_TOKEN`

```bash
CRM_ADMIN_TOKEN_VALUE="$(grep -E '^CRM_ADMIN_TOKEN=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ -z "$CRM_ADMIN_TOKEN_VALUE" ] || echo "$CRM_ADMIN_TOKEN_VALUE" | grep -Eq '^(choose_|replace-|your_|change-this|client123)'; then
  echo "ERROR: CRM_ADMIN_TOKEN must be a real secret."
elif [ "${#CRM_ADMIN_TOKEN_VALUE}" -lt 12 ]; then
  echo "ERROR: CRM_ADMIN_TOKEN must be at least 12 characters."
else
  echo "CRM_ADMIN_TOKEN OK."
fi
```

#### 5.4 Check `CLIENT_PANEL_DEFAULT_PASSWORD`

```bash
CLIENT_PANEL_DEFAULT_PASSWORD_VALUE="$(grep -E '^CLIENT_PANEL_DEFAULT_PASSWORD=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ -z "$CLIENT_PANEL_DEFAULT_PASSWORD_VALUE" ] || echo "$CLIENT_PANEL_DEFAULT_PASSWORD_VALUE" | grep -Eq '^(choose_|replace-|your_|change-this|client123)'; then
  echo "ERROR: CLIENT_PANEL_DEFAULT_PASSWORD must be a real password."
elif [ "${#CLIENT_PANEL_DEFAULT_PASSWORD_VALUE}" -lt 12 ]; then
  echo "ERROR: CLIENT_PANEL_DEFAULT_PASSWORD must be at least 12 characters."
else
  echo "CLIENT_PANEL_DEFAULT_PASSWORD OK."
fi
```

#### 5.5 Check `CLIENT_PANEL_TOKEN_SECRET`

```bash
CLIENT_PANEL_TOKEN_SECRET_VALUE="$(grep -E '^CLIENT_PANEL_TOKEN_SECRET=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ -z "$CLIENT_PANEL_TOKEN_SECRET_VALUE" ] || echo "$CLIENT_PANEL_TOKEN_SECRET_VALUE" | grep -Eq '^(choose_|replace-|your_|change-this|client123)'; then
  echo "ERROR: CLIENT_PANEL_TOKEN_SECRET must be a real signing secret."
elif [ "${#CLIENT_PANEL_TOKEN_SECRET_VALUE}" -lt 16 ]; then
  echo "ERROR: CLIENT_PANEL_TOKEN_SECRET must be at least 16 characters."
else
  echo "CLIENT_PANEL_TOKEN_SECRET OK."
fi
```

Generate strong values when needed:

```bash
openssl rand -base64 32
```

### 6. Compose Sanity Check

This verifies AI Hub is still only `app` and `db`, with no Docker Nginx.

```bash
cd /var/www/AI_salesman_plugin

echo "== compose sanity =="
if grep -q '127.0.0.1:5176:8585' docker-compose.yml; then
  echo "Port mapping OK."
else
  echo "ERROR: docker-compose.yml must expose app as 127.0.0.1:5176:8585."
fi
if grep -q '^  nginx:' docker-compose.yml; then
  echo "ERROR: docker-compose.yml must not contain a Docker nginx service."
else
  echo "No Docker nginx service OK."
fi
SERVICES="$(sudo docker compose config --services | sort | tr '\n' ' ')"
if [ "$SERVICES" != "app db " ]; then
  echo "ERROR: expected compose services 'app db', got: $SERVICES"
else
  echo "Compose services OK."
fi
echo "Continue only if all compose checks above say OK."
```

### 7. Pre-Build Docker Space Cleanup

Run this before every AI Hub build on the current server. It clears Docker build cache only; it does not touch containers, images, networks, or volumes.

#### 7.1 Inspect Disk Usage

```bash
cd /var/www/AI_salesman_plugin

echo "== host disk usage =="
df -h /
echo "== docker disk usage =="
sudo docker system df
```

#### 7.2 Clear Docker Build Cache

```bash
cd /var/www/AI_salesman_plugin

echo "== clear docker build cache =="
sudo docker builder prune -af
sudo docker system df
```

#### 7.3 Optional Stronger Cleanup

Run this only if disk usage is still tight after clearing build cache. It removes unused Docker images, stopped containers, and unused networks. It does not remove named volumes.

```bash
cd /var/www/AI_salesman_plugin

echo "== remove unused docker objects =="
sudo docker system prune -af
sudo docker system df
```

### 8. Build App Image

```bash
cd /var/www/AI_salesman_plugin

echo "== build app image =="
sudo docker compose build --no-cache app
```

### 9. Restart AI Hub Services

```bash
cd /var/www/AI_salesman_plugin

echo "== restart db and app =="
sudo docker compose up -d --force-recreate db app
sudo docker compose ps
```

### 10. Local Smoke

This checks the local container route and verifies CRM admin API auth works with `CRM_ADMIN_TOKEN`.

```bash
cd /var/www/AI_salesman_plugin

echo "== local smoke =="
curl -fsS http://127.0.0.1:5176/health >/dev/null \
  && echo "Health OK." \
  || echo "ERROR: local health failed."
curl -fsS http://127.0.0.1:5176/crm/ | grep -E 'assets/index-.*\.js' >/dev/null \
  && echo "CRM assets OK." \
  || echo "ERROR: CRM assets failed."
CRM_ADMIN_TOKEN_VALUE="$(grep -E '^CRM_ADMIN_TOKEN=' .env | tail -n 1 | cut -d= -f2- | tr -d "\"'")"
if [ -z "$CRM_ADMIN_TOKEN_VALUE" ]; then
  echo "ERROR: CRM_ADMIN_TOKEN missing in .env."
else
  curl -fsS http://127.0.0.1:5176/v1/admin/overview \
    -H "x-crm-admin-token: ${CRM_ADMIN_TOKEN_VALUE}" >/dev/null \
    && echo "CRM admin auth OK." \
    || echo "ERROR: CRM admin auth failed. Check CRM_ADMIN_TOKEN in .env and restart app after env changes."
fi
echo "Continue only if all local smoke checks above say OK."
```

## Public Smoke

Run after AI-KART's shared Nginx route has been applied.

```bash
curl -fsS http://143.198.5.97/aihub/health >/dev/null \
  && echo "Public health OK." \
  || echo "ERROR: public health failed."
curl -fsS http://143.198.5.97/aihub/crm/ | grep -E 'assets/index-.*\.js' >/dev/null \
  && echo "Public CRM assets OK." \
  || echo "ERROR: public CRM assets failed."
echo "Continue only if all public smoke checks above say OK."
```

If local `127.0.0.1:5176` works but public `/aihub/` fails, apply `/var/www/Vercel_website/aikart.md`.

## Docker Space Recovery

Use this if the normal pre-build cleanup above is not enough and Docker build or restart still fails because disk space is exhausted. Run one chunk at a time and read the output.

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
