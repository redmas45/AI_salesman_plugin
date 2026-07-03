# AI Hub Deploy

Target:

```text
Public domain: https://demo1.ergobite.com:3001
Server IP:     157.245.3.230
AI Hub repo:   /var/www/AI_salesman_plugin
Panel repo:    /var/www/client_panel
AI Hub local:  http://127.0.0.1:5176
AI Hub CRM:    https://demo1.ergobite.com:3001/aihub/crm/
Client panel:  https://demo1.ergobite.com:3001/aihub/client_panel/<site_id>
```

AI Hub runs through Docker Compose services `db` and `app`.
The client websites are independent and can run on separate domains.
Public HTTPS routing is handled by host Nginx.

## First-Time Deployment

Use this only on a new server.

### 1. SSH And Tmux

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 ev@157.245.3.230
tmux new -A -s aihub-deploy
```

### 2. Install Docker

Skip if Docker is already installed.

```bash
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker --version
docker compose version
```

### 3. Clone Repos

```bash
mkdir -p /var/www
cd /var/www
git clone https://github.com/redmas45/AI_salesman_plugin.git
git clone https://github.com/redmas45/client_panel.git
cd /var/www/AI_salesman_plugin
chmod +x docker/entrypoint.sh
```

`client_panel` must sit next to `AI_salesman_plugin` because Docker uses it as a build context.

### 4. Create `.env`

```bash
cd /var/www/AI_salesman_plugin
nano .env
```

Use this minimal Hub-only env:

```env
HUB_PUBLIC_URL=https://demo1.ergobite.com:3001/aihub
PUBLIC_API_URL=https://demo1.ergobite.com:3001/aihub
VOICE_ORB_API_URL=https://demo1.ergobite.com:3001/aihub
CORS_ORIGINS=https://demo1.ergobite.com:3001

DEPLOYMENT_MODE=public-domain

OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
CRM_ADMIN_TOKEN=replace_with_real_secret
CLIENT_PANEL_DEFAULT_PASSWORD=replace_with_real_password
CLIENT_PANEL_TOKEN_SECRET=replace_with_real_secret
```

Do not set `CURRENT_SITE_ID`, `DEFAULT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `CLIENT_STORE_URL`, or `CURRENT_URL` for Hub-only deploy.

Generate secrets:

```bash
openssl rand -base64 32
```

### 5. Build And Start

```bash
cd /var/www/AI_salesman_plugin
docker compose build app
docker compose up -d db app
docker compose ps
```

### 6. Install HTTPS

Requirements:

- `demo1.ergobite.com` DNS A record points to `157.245.3.230`.
- Firewall allows `80`, `443`, and `3001`.
- Nginx is installed on the host.

Open the required local firewall ports:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3001/tcp
ufw status
```

If `ufw status` says inactive, either enable it after confirming SSH is allowed or configure the cloud provider firewall instead:

```bash
ufw enable
```

```bash
apt update
apt install -y nginx certbot python3-certbot-nginx
certbot --nginx -d demo1.ergobite.com
```

If Certbot asks whether to redirect HTTP to HTTPS, choose option `2`.

The public URL intentionally uses port `3001`, so this server block must use `listen 3001 ssl;`.

Create the Nginx site:

```bash
nano /etc/nginx/sites-available/demo1.ergobite.com
```

Paste:

```nginx
server {
    listen 3001 ssl;
    server_name demo1.ergobite.com;

    ssl_certificate /etc/letsencrypt/live/demo1.ergobite.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/demo1.ergobite.com/privkey.pem;

    location = / {
        return 302 /aihub/crm/;
    }

    location = /aihub {
        return 301 /aihub/;
    }

    location /aihub/ {
        proxy_pass http://127.0.0.1:5176/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Prefix /aihub;
    }
}
```

Enable and reload:

```bash
ln -sf /etc/nginx/sites-available/demo1.ergobite.com /etc/nginx/sites-enabled/demo1.ergobite.com
nginx -t
systemctl reload nginx
ss -lntp | grep ':3001'
```

Check renewal:

```bash
certbot renew --dry-run
systemctl list-timers | grep certbot
```

### 7. Smoke Test

```bash
curl -fsS http://127.0.0.1:5176/health && echo OK
curl -fsS https://demo1.ergobite.com:3001/aihub/health && echo OK
```

If public smoke gives `502`, check local app first:

```bash
docker compose ps
docker compose logs --tail=100 app
curl -i http://127.0.0.1:5176/health
```

If the browser gives `ERR_CONNECTION_TIMED_OUT`, port `3001` is not reachable from the internet. Check:

```bash
ss -lntp | grep ':3001'
ufw status
```

Also check the cloud provider firewall/security group and allow inbound TCP `3001`.

## Normal CI/CD Deploy

Use this after first-time deployment is complete.

```bash
tmux new -A -s aihub-deploy

cd /var/www/AI_salesman_plugin
git pull --ff-only

cd /var/www/client_panel
git pull --ff-only

cd /var/www/AI_salesman_plugin
docker compose build app
docker compose up -d app
docker compose ps

curl -fsS http://127.0.0.1:5176/health && echo OK
curl -fsS https://demo1.ergobite.com:3001/aihub/health && echo OK
```

If either `git pull` refuses because of local edits:

```bash
git status --short
```

Inspect before stashing. If the edits are only server-local noise:

```bash
git stash push -m "server-before-deploy"
git pull --ff-only
```

## Updating `.env`

Use only when secrets or allowed origins change.

```bash
cd /var/www/AI_salesman_plugin
nano .env
docker compose up -d app
```

When adding an independent demo website, add that website origin to `CORS_ORIGINS`.

Example:

```env
CORS_ORIGINS=https://demo1.ergobite.com:3001,https://shop-demo.example.com
```

Do not put demo website domains into `HUB_PUBLIC_URL` or `PUBLIC_API_URL`; those stay pointed at AI Hub.

## Docker Notes

Normal deploy should use cached builds:

```bash
docker compose build app
docker compose up -d app
```

Do not use `--no-cache` unless a dependency layer is corrupted or a full rebuild is intentional.

Only if disk space is actually low:

```bash
docker system df
docker builder prune -af
```

Do not run this during normal deploy because named volumes may contain database data:

```bash
docker system prune --volumes
```
