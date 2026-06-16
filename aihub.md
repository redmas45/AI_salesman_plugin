# AI Hub Deployment

Use this for the current setup:

```text
AI-KART website: http://143.198.5.97/aikart/
AI Hub local:    http://127.0.0.1:5176
AI Hub public:   http://143.198.5.97/aihub/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
```

Both public apps share port `80` and are separated by URL path.
DNS is optional for this setup because both apps are accessed by `IP/path`.

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

CLIENT_STORE_URL=http://143.198.5.97/aikart/

CRAWL_ON_STARTUP=false
CRAWL_PERIODIC_ENABLED=false

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
CLIENT_STORE_URL=http://143.198.5.97/aikart/
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

This exposes both apps on port `80`:

```text
http://143.198.5.97/aikart/
http://143.198.5.97/aihub/
```

Copy this:

```bash
sudo tee /etc/nginx/sites-available/aikart-aihub-paths >/dev/null <<'EOF'
map $http_upgrade $connection_upgrade_aihub {
    default upgrade;
    "" close;
}

server {
    listen 80 default_server;
    server_name 143.198.5.97 _;

    client_max_body_size 25m;

    location = / {
        return 302 /aikart/;
    }

    location = /aikart {
        return 301 /aikart/;
    }

    location /aikart/ {
        proxy_pass http://127.0.0.1:5175/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
        proxy_set_header X-Forwarded-Prefix /aikart;
    }

    location / {
        proxy_pass http://127.0.0.1:5175;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }

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
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/aikart
sudo rm -f /etc/nginx/sites-enabled/aihub
sudo ln -sfn /etc/nginx/sites-available/aikart-aihub-paths /etc/nginx/sites-enabled/aikart-aihub-paths
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Check Nginx File

Copy this:

```bash
sudo grep -nE 'listen|server_name|location|proxy_pass' /etc/nginx/sites-available/aikart-aihub-paths
```

You should see:

```text
listen 80
server_name 143.198.5.97 _
location /aikart/
proxy_pass http://127.0.0.1:5175/
location /aihub/
proxy_pass http://127.0.0.1:5176/
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

Copy this:

```bash
cd /var/www/AI_salesman_plugin
sudo docker compose exec app python -c "from agent.ingestion import sync_web_crawl; sync_web_crawl('http://143.198.5.97/aikart/', max_pages=1024, max_depth=100, site_id='ai_kart_main', reconcile_missing=True, source_name='crm_crawler')"
```

## 10. Test AI Answer

Copy this:

```bash
curl -s -X POST http://127.0.0.1:5176/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have dog sweater?","site_id":"ai_kart_main"}'
```

## 11. Put Script In AI-KART

Only do this after AI Hub works at `http://143.198.5.97/aihub/health`.

Copy this:

```bash
cd /var/www/Vercel_website

python - <<'PY'
from pathlib import Path
import re

path = Path("out/index.html")
html = path.read_text(encoding="utf-8")
html = re.sub(
    r'<script\b[^>]*\bsrc=(["\'])[^"\']*/shopbot\.js(?:\?[^"\']*)?\1[^>]*>\s*</script>\s*',
    "",
    html,
    flags=re.IGNORECASE,
)
script = '<script defer src="http://143.198.5.97/aihub/shopbot.js?site=ai_kart_main" data-site-id="ai_kart_main" data-api-url="http://143.198.5.97/aihub"></script>'
html = html.replace("</body>", script + "\n</body>", 1)
path.write_text(html, encoding="utf-8")
PY

pm2 restart ai-kart --update-env
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
