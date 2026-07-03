# AI Hub Deploy

Target:

```text
Public domain: https://demo1.ergobite.com
Server IP:     157.245.3.230
AI Hub repo:   /var/www/AI_salesman_plugin
Panel repo:    /var/www/client_panel
AI Hub local:  http://127.0.0.1:3002
AI Hub CRM:    https://demo1.ergobite.com/crm/
Client panel:  https://demo1.ergobite.com/client_panel/<site_id>
```

AI Hub runs through Docker Compose services `db` and `app`.
The client websites are independent and can run on separate domains.
Public HTTPS routing is handled by host Nginx.

The important deployment rule:

```text
Internet/browser -> https://demo1.ergobite.com/ on port 443
Nginx            -> http://127.0.0.1:3002/ private local app port
Docker app       -> container port 8585
```

Do not expose public `:3002`. Port `3002` is only for Nginx on the same server.

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

### 4. Set Local App Port

Create a server-only Compose override so the app listens privately on localhost port `3002`:

```bash
cd /var/www/AI_salesman_plugin
nano docker-compose.override.yml
```

Paste:

```yaml
services:
  app:
    ports:
      - "127.0.0.1:3002:8585"
```

This keeps the app reachable by Nginx on the server, but not directly from the public internet.

### 5. Create `.env`

```bash
cd /var/www/AI_salesman_plugin
nano .env
```

Use this minimal Hub-only env:

```env
HUB_PUBLIC_URL=https://demo1.ergobite.com
PUBLIC_API_URL=https://demo1.ergobite.com
VOICE_ORB_API_URL=https://demo1.ergobite.com
CORS_ORIGINS=https://demo1.ergobite.com

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

### 6. Build And Start

```bash
cd /var/www/AI_salesman_plugin
docker compose build app
docker compose up -d db app
docker compose ps
```

Verify the private local app is listening:

```bash
curl -fsS http://127.0.0.1:3002/health && echo OK
```

### 7. Configure Nginx and HTTPS

Since the Nginx configuration file `/etc/nginx/sites-available/demo1.ergobite.com.conf` and the SSL certificates are already in place, you only need to ensure the config is enabled and Nginx is reloaded.

Requirements:

- Firewall allows public `80` and `443`.
- Nginx is installed on the host.

Open the required local firewall ports:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw status
```

If `ufw status` says `inactive`, enable it:

> [!WARNING]
> When you run `ufw enable`, it will prompt:
> `Command may disrupt existing ssh connections. Proceed with operation (y|n)?`
> Make sure `ufw allow OpenSSH` (or `ufw allow 22/tcp`) was run successfully first, then type `y` to proceed. Otherwise, you will be locked out!

```bash
ufw enable
```

#### Nginx Site Configuration

Verify that `/etc/nginx/sites-available/demo1.ergobite.com.conf` matches:

```nginx
server {
    server_name demo1.ergobite.com;

    location = / {
        return 302 /crm/;
    }

    location / {
        proxy_pass http://127.0.0.1:3002;

        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/demo1.ergobite.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/demo1.ergobite.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = demo1.ergobite.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name demo1.ergobite.com;
    return 404; # managed by Certbot
}
```

Enable the configuration (if not already enabled) and reload Nginx:

```bash
ln -sf /etc/nginx/sites-available/demo1.ergobite.com.conf /etc/nginx/sites-enabled/demo1.ergobite.com.conf
nginx -t
systemctl reload nginx
ss -lntp | grep ':443'
```

Check renewal:

```bash
certbot renew --dry-run
systemctl list-timers | grep certbot
```

### 8. Smoke Test

```bash
curl -fsS http://127.0.0.1:3002/health && echo OK
curl -fsS https://demo1.ergobite.com/health && echo OK
```

If public smoke gives `502`, check local app first:

```bash
docker compose ps
docker compose logs --tail=100 app
curl -i http://127.0.0.1:3002/health
```

If `https://demo1.ergobite.com/` gives `ERR_CONNECTION_TIMED_OUT`, check public HTTPS:

```bash
ss -lntp | grep ':443'
ufw status
```

Server-side `curl https://demo1.ergobite.com/health` can pass even when the public internet is blocked by the cloud firewall. Test from your local machine too.

On Windows PowerShell:

```powershell
Test-NetConnection demo1.ergobite.com -Port 443
```

Also check the cloud provider firewall/security group and allow inbound TCP `443`.

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

curl -fsS http://127.0.0.1:3002/health && echo OK
curl -fsS https://demo1.ergobite.com/health && echo OK
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
CORS_ORIGINS=https://demo1.ergobite.com,https://shop-demo.example.com
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
