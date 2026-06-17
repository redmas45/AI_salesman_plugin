# AI-KART Website Deployment

Use this for the standalone setup (FastAPI Backend + React/Vite Frontend):

```text
AI-KART public: http://aikart.ergobite.com  (or server IP on port 80)
AI-KART backend:http://127.0.0.1:8000
AI-KART front:  http://127.0.0.1:5175
Project:        /var/www/Vercel_website
Venv:           /Data/www/aikartvenv
```

## 1. Fix Permissions

```bash
cd /var/www/Vercel_website
sudo chown -R $(whoami):$(whoami) /var/www/Vercel_website
sudo chown -R $(whoami):$(whoami) /Data/www/aikartvenv
```

## 2. Install Project Node

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

export PATH="/var/www/Vercel_website/.node/current/bin:$PATH"
node -v
npm -v
```

## 3. Create `.env`

Create the environments for both frontend and backend:

```bash
# Backend config
cat > /var/www/Vercel_website/backend/.env <<'EOF'
DATABASE_URL=sqlite+aiosqlite:///./aikart.db
# Allows local proxy, public IP, and the custom domain
CORS_ORIGINS=http://143.198.5.97,http://aikart.ergobite.com,http://127.0.0.1:5175,http://localhost:5175
# This origin determines the CSP policy for the widget
SHOPBOT_HUB_ORIGIN=http://143.198.5.97/aihub
EOF

# Frontend config
cat > /var/www/Vercel_website/frontend/.env.local <<'EOF'
# API runs on the same domain as the frontend, so we leave this blank
VITE_API_BASE_URL=
# The AI Hub injection script
VITE_SHOPBOT_HUB_ORIGIN=http://143.198.5.97/aihub
VITE_SHOPBOT_SITE_ID=ai_kart_main
EOF
```

## 4. Build Website

```bash
cd /var/www/Vercel_website/backend
source /Data/www/aikartvenv/bin/activate
python -m pip install -r requirements.txt

cd /var/www/Vercel_website/frontend
export PATH="/var/www/Vercel_website/.node/current/bin:$PATH"
rm -rf node_modules
npm install
npm run build
```

## 5. Start Website (PM2)

Start the FastAPI backend and Vite frontend separately:

```bash
# Start Backend
cd /var/www/Vercel_website/backend
source /Data/www/aikartvenv/bin/activate
pm2 describe ai-kart-backend >/dev/null \
  && pm2 restart ai-kart-backend \
  || pm2 start "uvicorn app.main:app --host 127.0.0.1 --port 8000" --name ai-kart-backend --cwd /var/www/Vercel_website/backend

# Start Frontend
cd /var/www/Vercel_website/frontend
export PATH="/var/www/Vercel_website/.node/current/bin:$PATH"
pm2 describe ai-kart-frontend >/dev/null \
  && pm2 restart ai-kart-frontend \
  || pm2 start "npm run preview -- --port 5175 --host 127.0.0.1" --name ai-kart-frontend --cwd /var/www/Vercel_website/frontend

pm2 save
pm2 list
```

## 6. Create Nginx Config (Root Path)

This setup treats AI-KART as a completely independent website at the root path (`/`).

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

    # Route API calls to the backend
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
        # If connection_upgrade mapping is missing, just use upgrade directly
        proxy_set_header Connection $connection_upgrade_aihub; 
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Route all other traffic to the React frontend
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
sudo rm -f /etc/nginx/sites-enabled/aikart-aihub-paths
sudo ln -sfn /etc/nginx/sites-available/aikart-standalone /etc/nginx/sites-enabled/aikart-standalone
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Test AI-KART

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5175/
curl -s -o /dev/null -w "%{http_code}\n" http://143.198.5.97/api/products
```

Expected:
```text
200
200
```
