# AI Hub Deployment

Use this for the current setup:

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
```

All public apps share port `80` and are separated by URL paths:

```text
/                  -> AI-KART website
/api/              -> AI-KART backend
/aihub/            -> AI Hub
/client-panel/<client_id> -> Client Panel
```

DNS is optional for this setup because all apps are accessed by `IP`.

If you are starting from an empty server, deploy AI Hub first through step 5. Then deploy AI-KART from `/var/www/Vercel_website/aikart.md` and Client Panel from `/var/www/client_panel/clientpanel.md`; the AI-KART guide owns the shared public Nginx routing for `/`, `/api/`, `/aihub/`, and `/client-panel/`. After AI-KART works and `/aihub/` is routed, come back here and run steps 8 through 10.

For this deployment, run step 4 exactly. The React CRM is built inside the Hub Docker image, and the old browser-prompt CRM can remain live if you only restart containers or reuse a cached image.

## 1. Fix Permissions

Copy this:

```bash
cd /var/www/AI_salesman_plugin
sudo chown -R $(whoami):$(whoami) /var/www/AI_salesman_plugin
chmod +x /var/www/AI_salesman_plugin/docker/entrypoint.sh
mkdir -p /var/www/AI_salesman_plugin/data
mkdir -p /var/www/AI_salesman_plugin/deploy/certs
sudo chown -R $(whoami):$(whoami) /var/www/AI_salesman_plugin/data /var/www/AI_salesman_plugin/deploy/certs
```

## 2. Create `.env`

Copy this:

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

OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
CRM_ADMIN_TOKEN=choose_strong_token
CLIENT_PANEL_DEFAULT_PASSWORD=choose_client_panel_password
CLIENT_PANEL_TOKEN_SECRET=choose_client_panel_token_secret
EOF
```

Now edit only these five values:

```bash
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

Do not change `CLIENT_STORE_URL` or `CURRENT_URL` right now. They should stay:

```text
CLIENT_STORE_URL=http://143.198.5.97/
CURRENT_URL=http://143.198.5.97/
```

## 3. Set Docker To Local Port `5176`

Copy this:

```bash
cd /var/www/AI_salesman_plugin

python - <<'PY'
from pathlib import Path

path = Path("docker-compose.yml")
text = path.read_text(encoding="utf-8")
text = text.replace('      - "8585:8585"', '      - "127.0.0.1:5176:8585"')
path.write_text(text, encoding="utf-8")
PY

sudo docker compose stop nginx || true
sudo docker compose rm -f nginx || true
```

## 4. Pull Latest Code And Start AI Hub With Fresh CRM Build

Copy this:

```bash
cd /var/www/AI_salesman_plugin
git pull
sudo docker compose build --no-cache app
sudo docker compose up -d --force-recreate db app
sudo docker compose ps
```

You should see `db` and `app` running.

Use `build --no-cache app` and `up --force-recreate` here. Do not only run `docker compose restart`, because the CRM bundle and crawler code are built into the app image.

This guide uses system Nginx, so only `db` and `app` are recreated. If your server is still using the old Docker Nginx container, use this instead:

```bash
sudo docker compose build --no-cache app
sudo docker compose up -d --force-recreate db app nginx
```

## 5. Test Local AI Hub

Copy this:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5176/health
curl -s http://127.0.0.1:5176/crm/ | grep -E 'assets/index-.*\.js'
curl -s http://127.0.0.1:5176/crm/app.js | grep 'crm_reload'
curl -s http://127.0.0.1:5176/crm/app.js | grep -q 'prompt(' && echo "ERROR: old CRM app.js still served" || echo "OK: no old prompt app.js"
```

Expected:

```text
200
current CRM bundle path
legacy reload shim
OK: no old prompt app.js
```

If `/crm/` still references `app.js` and `styles.css`, the server is running the old CRM image. Rebuild the Hub app image instead of only restarting:

```bash
sudo docker compose build --no-cache app
sudo docker compose up -d --force-recreate db app
```

Do not open the CRM in the browser until these checks pass.

## 6. Public Routing Requirement

AI Hub should only expose this local upstream from its own deployment:

```text
http://127.0.0.1:5176
```

The public `/aihub/` route is edge/shared Nginx config. In the current same-IP setup, AI-KART owns `/` and `/api/`, so the shared Nginx block belongs in `/var/www/Vercel_website/aikart.md`.

Do not add AI-KART `/`, `/api/`, Client Panel `/client-panel/`, or frontend proxy rules in this Hub guide. If you later use a dedicated hostname such as `aihub.ergobite.com`, configure that hostname in Nginx to proxy directly to `http://127.0.0.1:5176`.

After AI-KART/shared Nginx is deployed, test the public Hub routes:

Copy this:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5176/health
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aihub/health
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aihub/crm/
curl -s http://143.198.5.97/aihub/crm/ | grep -E 'assets/index-.*\.js'
curl -s http://143.198.5.97/aihub/crm/app.js | grep 'crm_reload'
curl -s http://143.198.5.97/aihub/crm/app.js | grep -q 'prompt(' && echo "ERROR: old public CRM app.js still served" || echo "OK: no old public prompt app.js"
```

Expected:

```text
200
200
200
current CRM bundle path
legacy reload shim
OK: no old public prompt app.js
```

If Chrome still shows the old `143.198.5.97 says CRM admin token` prompt after these checks pass, hard refresh the CRM tab with `Ctrl+Shift+R`. The server will now serve no-cache CRM files, so this should only be a browser cache cleanup.

## 7. Create/Update AI-KART Client In CRM

Open:

```text
http://143.198.5.97/aihub/crm/
```

Use the CRM admin token from `CRM_ADMIN_TOKEN`.

Create or update the AI-KART client with:

```text
Site ID: ai_kart
Website URL: http://143.198.5.97/
Enabled: yes
```

## 8. Crawl AI-KART

Because AI-KART is now served on the root path `/` instead of `/aikart/`, use the root URL.

The Hub is configured to crawl once during startup and then every 120 seconds. Run this manual crawl after AI-KART is reachable anyway, because it proves the live website catalog is populated before testing customer questions.

Copy this:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/', max_pages=1024, max_depth=100, site_id='ai_kart', reconcile_missing=True, source_name='crm_crawler')"
```

## 9. Test AI Answer

Copy this:

```bash
curl -s -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart"}'
```

## 10. Verify Script In AI-KART

Copy this:

```bash
curl -s http://143.198.5.97/ | grep '143.198.5.97/aihub/shopbot.js'
```

## 11. Later

Optional DNS records:

```text
aikart.ergobite.com -> 143.198.5.97
aihub.ergobite.com  -> 143.198.5.97
```

With DNS hostname routing, use:

```text
http://aikart.ergobite.com
http://aihub.ergobite.com
```

Later, switch from path routing to hostname routing if you want separate clean domains. Voice microphone testing needs HTTPS.
