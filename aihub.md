# AI Hub Deployment

Use this for the current setup:

```text
AI-KART website: http://143.198.5.97/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
```

Both public apps share port `80`. AI-KART is on the root `/`, and AI Hub is separated by the `/aihub/` URL path.
DNS is optional for this setup because both apps are accessed by `IP`.

If you are starting from an empty server, deploy AI Hub first through step 8. Then deploy AI-KART from `aikart.md`. After AI-KART works, come back here and run steps 9 through 11.

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

CURRENT_SITE_ID=ai_kart_main
DEFAULT_SITE_ID=ai_kart_main
AI_DEFAULT_SITE_ID=ai_kart_main

CLIENT_STORE_URL=http://143.198.5.97/

CRAWL_ON_STARTUP=true
CRAWL_PERIODIC_ENABLED=true

OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
CRM_ADMIN_TOKEN=choose_strong_token
EOF
```

Now edit only these three values:

```bash
nano /var/www/AI_salesman_plugin/.env
```

Replace:

```text
your_openai_key
your_groq_key
choose_strong_token
```

Do not change `CLIENT_STORE_URL` right now. It should stay:

```text
CLIENT_STORE_URL=http://143.198.5.97/
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

## 4. Start AI Hub

Copy this:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose up -d --build --force-recreate db app
sudo docker compose ps
```

You should see `db` and `app` running.

## 5. Test Local AI Hub

Copy this:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5176/health
```

Expected:

```text
200
```

## 6. Create Shared Nginx Path Config

This configuration serves the standalone AI-KART on the root path `/` and AI Hub on `/aihub/`. 
*(Note: If you already ran this from the `aikart.md` guide, you do not need to run it again.)*

Copy this:

```bash
sudo tee /etc/nginx/sites-available/aikart-standalone >/dev/null <<'EOF'
map $http_upgrade $connection_upgrade_aihub {
    default upgrade;
    "" close;
}

server {
    listen 80;
    server_name aikart.ergobite.com 143.198.5.97 _;

    client_max_body_size 25m;

    # Route API calls to the AI-KART backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }

    # Proxy AI-Hub
    location = /aihub {
        return 301 /aihub/;
    }

    location = /aihub/ {
        return 302 /aihub/crm/;
    }

    location /aihub/ {
        proxy_pass http://127.0.0.1:5176/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
        proxy_set_header X-Forwarded-Prefix /aihub;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade_aihub; 
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Route all other traffic to the React frontend (root)
    location / {
        proxy_pass http://127.0.0.1:5175/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/aikart
sudo rm -f /etc/nginx/sites-enabled/aihub
sudo rm -f /etc/nginx/sites-enabled/aikart-aihub-paths
sudo ln -sfn /etc/nginx/sites-available/aikart-standalone /etc/nginx/sites-enabled/aikart-standalone
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Check Nginx File

Copy this:

```bash
sudo grep -nE 'listen|server_name|location|proxy_pass' /etc/nginx/sites-available/aikart-standalone
```

## 8. Test AI Hub Through Nginx

Copy this:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5176/health
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aihub/health
```

Expected:

```text
200
200
```

## 9. Crawl AI-KART

Because AI-KART is now served on the root path `/` instead of `/aikart/`, use the root URL.

Copy this:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/', max_pages=1024, max_depth=100, site_id='ai_kart_main', reconcile_missing=True, source_name='crm_crawler')"
```

## 10. Test AI Answer

Copy this:

```bash
curl -s -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart_main"}'
```

## 11. Verify Script In AI-KART

Copy this:

```bash
curl -s http://143.198.5.97/ | grep '143.198.5.97/aihub/shopbot.js'
```

## 12. Later

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
