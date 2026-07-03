# AI Hub Deploy

Target:

```text
Public domain: https://demo1.ergobite.com:3001
Server IP:     157.245.3.230
Project path:  /var/www/AI_salesman_plugin
AI Hub local:  http://127.0.0.1:5176
AI Hub public: https://demo1.ergobite.com:3001/aihub/
AI Hub CRM:    https://demo1.ergobite.com:3001/aihub/crm/
Client panel:  https://demo1.ergobite.com:3001/aihub/client_panel/<site_id>
```

AI Hub runs through Docker Compose services `db` and `app`.
Public routing is handled by the shared host Nginx config, not by this repo.
The browser mic needs HTTPS on the storefront page, so public URLs must use `https://`.

## What The Folders Are

- `/var/www/AI_salesman_plugin` is the project checkout.
- `/var/www/AI_salesman_plugin/data` is local runtime data created by the app/crawler. It is not code.
- `deploy/` has old/optional deployment assets. For this server, shared Nginx owns routing, so you do not need to touch `deploy/`.

## Fresh Server Setup

SSH into the server:

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 ev@157.245.3.230
```

Use `tmux` so Docker keeps running if SSH disconnects:

```bash
tmux new -A -s aihub-deploy
```

Clone the repo:

```bash
sudo mkdir -p /var/www
sudo chown "$(whoami):$(whoami)" /var/www
cd /var/www
git clone https://github.com/redmas45/AI_salesman_plugin.git
git clone https://github.com/redmas45/client_panel.git
cd /var/www/AI_salesman_plugin
chmod +x docker/entrypoint.sh
```

`client_panel` must sit next to `AI_salesman_plugin` because Docker uses it as a build context.

Create `.env`:

```bash
nano .env
```

Set these values in `.env`:

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

Do not set `CURRENT_SITE_ID`, `DEFAULT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `CLIENT_STORE_URL`, or `CURRENT_URL` for the Hub-only deploy.
Those are demo/client-site settings. Add them later only when you intentionally want startup crawling or a fixed fallback client.

Generate secrets when needed:

```bash
openssl rand -base64 32
```

Build and start:

```bash
docker compose build app
docker compose up -d db app
docker compose ps
```

## HTTPS Certificate

Do this before the public smoke test.
Certbot certificates last about 90 days and Certbot installs an auto-renew timer.

Requirements:

- `demo1.ergobite.com` DNS A record points to `157.245.3.230`.
- Firewall allows ports `80`, `443`, and `3001`.
- Nginx is installed on the host and owns the public route.

Install Certbot:

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

Issue the certificate. If Certbot asks whether to redirect HTTP to HTTPS, choose option `2`.

```bash
sudo certbot --nginx -d demo1.ergobite.com
```

If the site must stay on port `3001`, edit an Nginx site file. Do not paste the `listen`, `server_name`, or `ssl_certificate` lines directly into the terminal; they are Nginx config lines.

Open the file:

```bash
sudo nano /etc/nginx/sites-available/demo1.ergobite.com
```

Paste this full server block:

```nginx
server {
    listen 3001 ssl;
    server_name demo1.ergobite.com;

    ssl_certificate /etc/letsencrypt/live/demo1.ergobite.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/demo1.ergobite.com/privkey.pem;

    location /aihub/ {
        proxy_pass http://127.0.0.1:5176/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Prefix /aihub;
    }
}
```

Enable the site:

```bash
sudo ln -sf /etc/nginx/sites-available/demo1.ergobite.com /etc/nginx/sites-enabled/demo1.ergobite.com
```

Then reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Check renewal:

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

Local smoke:

```bash
curl -fsS http://127.0.0.1:5176/health && echo OK
```

Public smoke after Nginx is pointed at this app:

```bash
curl -fsS https://demo1.ergobite.com:3001/aihub/health && echo OK
```

## Normal Update Deploy

Use this after the first deploy:

```bash
cd /var/www/AI_salesman_plugin
git pull --ff-only
cd /var/www/client_panel
git pull --ff-only
cd /var/www/AI_salesman_plugin
docker compose build app
docker compose up -d app
docker compose ps
```

If `git pull` refuses because the server has local edits:

```bash
cd /var/www/AI_salesman_plugin
git status --short
git stash push -m "server-before-deploy"
git pull --ff-only
```

## Docker Notes

Use cached builds for normal deploys:

```bash
docker compose build app
docker compose up -d app
```

Do not use `--no-cache` unless a dependency layer is corrupted or you intentionally want a full rebuild.

Only if disk space is actually low:

```bash
docker system df
docker builder prune -af
```

Do not run this during normal deploy because named volumes may contain database data:

```bash
docker system prune --volumes
```

## Add Demo Websites Later

The Hub is deployed on `demo1.ergobite.com`.
Your demo websites can live on different domains.
Their owner/client panels still open from AI Hub, for example:

```text
https://demo1.ergobite.com:3001/aihub/client_panel/site_1
https://demo1.ergobite.com:3001/aihub/client_panel/site_2
```

When a demo website is ready:

1. Add it as a client in CRM.
2. Use that client's generated install script on the demo website.
3. Add the demo website origin to `CORS_ORIGINS`, then restart the app.

Example for a later demo website:

```bash
cd /var/www/AI_salesman_plugin
nano .env
docker compose up -d app
```

For example, if a demo site is `https://shop-demo.example.com`, include it:

```env
CORS_ORIGINS=https://demo1.ergobite.com:3001,https://shop-demo.example.com
```

Do not put demo website domains into `HUB_PUBLIC_URL` or `PUBLIC_API_URL`; those must stay pointed at AI Hub.

## Ownership

- AI Hub secrets live in `/var/www/AI_salesman_plugin/.env`.
- Demo website backend/admin secrets live in each demo website repo, not here.
- Shared public routing belongs in the host Nginx config.
