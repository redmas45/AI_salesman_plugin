# AI-KART Website Deployment

Use this for the current setup:

```text
AI-KART public: http://143.198.5.97/aikart/
AI Hub public:  http://143.198.5.97/aihub/
AI-KART local:  http://127.0.0.1:5175
Project:        /var/www/Vercel_website
Venv:           /Data/www/aikartvenv
PM2 app:        ai-kart
```

AI-KART is the client website. Do not put AI Hub config in AI-KART `.env`.
Both public apps share port `80` and are separated by URL path.

## 1. Fix Permissions

Copy this:

```bash
cd /var/www/Vercel_website
sudo chown -R $(whoami):$(whoami) /var/www/Vercel_website
sudo chown -R $(whoami):$(whoami) /Data/www/aikartvenv
```

## 2. Install Project Node

Copy this:

```bash
cd /var/www/Vercel_website

ARCH="$(uname -m)"

if [ "$ARCH" = "x86_64" ]; then
  NODE_ARCH="x64"
elif [ "$ARCH" = "aarch64" ]; then
  NODE_ARCH="arm64"
else
  echo "Unsupported arch: $ARCH"
  exit 1
fi

mkdir -p /var/www/Vercel_website/.node
cd /var/www/Vercel_website/.node

NODE_FILE="$(curl -fsSL https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt | grep "linux-${NODE_ARCH}.tar.xz" | awk '{print $2}' | head -n 1)"

curl -fsSLO "https://nodejs.org/dist/latest-v22.x/${NODE_FILE}"
tar -xf "$NODE_FILE"
ln -sfn "${NODE_FILE%.tar.xz}" current

cd /var/www/Vercel_website
export PATH="/var/www/Vercel_website/.node/current/bin:$PATH"
node -v
npm -v
```

## 3. Create `.env`

Copy this:

```bash
cat > /var/www/Vercel_website/.env <<'EOF'
STOREFRONT_HOST=127.0.0.1
STOREFRONT_PORT=5175

PUBLIC_BASE_URL=http://143.198.5.97/aikart
CATALOG_BASE_URL=http://143.198.5.97/aikart
CATALOG_API_URL=http://143.198.5.97/aikart/api/products
API_CORS_ORIGIN=*

ENABLE_AI_WIDGET=true
SHOPBOT_SITE_ID=ai_kart_main
SHOPBOT_BRAND=AI-KART
SHOPBOT_HUB_ORIGIN=http://143.198.5.97/aihub
SHOPBOT_API_URL=http://143.198.5.97/aihub
SHOPBOT_BACKEND_ORIGIN=http://127.0.0.1:5176
SHOPBOT_SCRIPT_SRC=http://143.198.5.97/aihub/shopbot.js?site=ai_kart_main
EOF
```

## 4. Build Website

Copy this:

```bash
cd /var/www/Vercel_website
source /Data/www/aikartvenv/bin/activate
export PATH="/var/www/Vercel_website/.node/current/bin:$PATH"

python -m pip install -r requirements.txt
python -m pip install uvicorn python-multipart

rm -rf node_modules
npm install
npm run build
```

## 5. Start Website

Copy this:

```bash
cd /var/www/Vercel_website
source /Data/www/aikartvenv/bin/activate

pm2 describe ai-kart >/dev/null \
  && pm2 restart ai-kart --update-env \
  || pm2 start /var/www/Vercel_website/run.py --name ai-kart --cwd /var/www/Vercel_website --interpreter /Data/www/aikartvenv/bin/python

pm2 save
pm2 list
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

## 7. Test AI-KART

Copy this:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5175/
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/aikart/
```

Expected:

```text
200
200
```

## 8. Verify AI Hub Script

Only do this after AI Hub works at `http://143.198.5.97/aihub/health`.
The build should already inject the AI Hub script into every generated page from `.env`.

Copy this:

```bash
cd /var/www/Vercel_website

pm2 restart ai-kart --update-env
curl -s http://143.198.5.97/aikart/ | grep '143.198.5.97/aihub/shopbot.js'
```

## 9. Later

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
