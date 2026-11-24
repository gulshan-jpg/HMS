# CheckinOS Production Launch Runbook

This guide details the step-by-step deployment procedure to take CheckinOS live into a production Kubernetes, Docker Swarm, AWS ECS, or bare-metal VPS environment.

---

## 1. Pre-Flight Checklist

Before launching, verify the following prerequisites:
- [ ] Production domain registered (e.g., `checkinos.io`). Wildcard DNS record configured: `*.checkinos.io` and `checkinos.io` pointing to your load balancer or reverse proxy.
- [ ] Managed PostgreSQL 16+ instance provisioned (AWS RDS, Supabase, Neon, or self-hosted) with automated point-in-time recovery (PITR) enabled.
- [ ] Stripe Account activated (Live Mode keys, Products & Prices configured).
- [ ] SendGrid (or AWS SES / Postmark) account verified with SPF, DKIM, and DMARC DNS records.
- [ ] S3 or Cloudflare R2 bucket provisioned for persistent backups and hotel logo uploads (optional for single-node volume deployments).
- [ ] SSL/TLS certificates issued via Let's Encrypt (Certbot) or Cloudflare.

---

## 2. Environment Configuration

Create a secure production `.env` file (`chmod 600 .env`). Never commit this file to version control.

```bash
# Core Environment
ENV=prod
DEBUG=false
ROOT_DOMAIN=checkinos.io
PORT=8000

# Security & Cryptography
# Generate with: openssl rand -hex 32
SECRET_KEY=e83a7f6c1b9d4e5f0a2c8b7d9e1f3a5c7b9d1e3f5a7c9b1d3e5f7a9c1b3d5e7
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Database (PostgreSQL 16+)
DATABASE_URL=postgresql+psycopg2://checkinos_user:super_secret_db_password@db.checkinos.internal:5432/checkinos_prod

# Stripe Billing (Live Mode)
STRIPE_SECRET_KEY=your_stripe_live_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_signing_secret
STRIPE_PRICE_STARTER=price_starter_monthly
STRIPE_PRICE_PRO=price_pro_monthly
STRIPE_PRICE_ENTERPRISE=price_enterprise_monthly

# Email Delivery (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key_here
FROM_EMAIL=notifications@checkinos.io
FROM_NAME="CheckinOS Hospitality Support"

# CORS & Trusted Origins
CORS_ORIGINS=https://checkinos.io,https://*.checkinos.io

# Operational Defaults
HOTEL_NAME="Grand Azure Resort & Spa"
HOTEL_CURRENCY=INR
HOTEL_TIMEZONE=Asia/Kolkata
HOTEL_TAX_RATE=0.12
```

---

## 3. Database Migration Runbook

CheckinOS uses **Alembic** for all declarative schema migrations. Never run `create_all()` in production.

```bash
# 1. Verify current database connection
python -c "from app.database import engine; conn = engine.connect(); print('Connected successfully'); conn.close()"

# 2. Inspect pending migration history
alembic current
alembic history

# 3. Apply all pending migrations to HEAD
alembic upgrade head

# 4. Verify head status
alembic current
# Output should display: 0016_user_org_memberships (head)
```

---

## 4. Stripe Webhook Setup

1. Log in to the [Stripe Dashboard](https://dashboard.stripe.com/webhooks).
2. Click **Add endpoint**.
3. Endpoint URL: `https://checkinos.io/api/billing/webhook` (or `https://api.checkinos.io/api/billing/webhook`).
4. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the **Signing secret** (`whsec_...`) and place it in `.env` as `STRIPE_WEBHOOK_SECRET`.
6. Test delivery locally via Stripe CLI if needed:
   ```bash
   stripe listen --forward-to localhost:8000/api/billing/webhook
   ```

---

## 5. Reverse Proxy & Wildcard Subdomain Routing (Nginx)

CheckinOS dynamically resolves tenant organizations from incoming subdomains (e.g. `thegrandpalace.checkinos.io`). Configure Nginx to pass the full `Host` header to Uvicorn.

```nginx
# /etc/nginx/sites-available/checkinos.conf

upstream checkinos_backend {
    server 127.0.0.1:8000 fail_timeout=0;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name checkinos.io *.checkinos.io;
    return 301 https://$host$request_uri;
}

# HTTPS Server Block (Wildcard)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name checkinos.io *.checkinos.io;

    ssl_certificate /etc/letsencrypt/live/checkinos.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/checkinos.io/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client body limit (supports CSV imports & logo uploads)
    client_max_body_size 25M;

    # Static assets caching
    location /static/ {
        alias /var/www/checkinos/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # Proxy to FastAPI / Uvicorn
    location / {
        proxy_pass http://checkinos_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        proxy_buffering off;
    }
}
```

---

## 6. Process Supervision with Systemd

```ini
# /etc/systemd/system/checkinos.service

[Unit]
Description=CheckinOS Production PMS Server
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/checkinos
EnvironmentFile=/var/www/checkinos/.env
ExecStart=/var/www/checkinos/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    --log-config /var/www/checkinos/logging_prod.json
Restart=always
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

```bash
# Reload and start service
sudo systemctl daemon-reload
sudo systemctl enable checkinos
sudo systemctl start checkinos
sudo systemctl status checkinos
```

---

## 7. Automated Daily Database Backups (Cron)

Set up an automated offsite backup cron running at 02:00 UTC daily:

```bash
# /etc/cron.d/checkinos-backup
0 2 * * * www-data pg_dump -Fc checkinos_prod | gzip > /var/backups/checkinos_$(date +\%Y\%m\%d_\%H\%M\%S).dump.gz && find /var/backups/ -name "checkinos_*.dump.gz" -mtime +30 -delete
```

---

## 8. Verification & Smoke Testing

Execute the production health probes:

```bash
# Liveness probe
curl -I https://checkinos.io/healthz
# HTTP/2 200
# {"status":"ok","db":"ok"}

# Readiness probe
curl -s https://checkinos.io/readyz | jq
# {"status":"ready","checks":{"database":"ok","disk_space":"ok (142.4 GB free)"}}

# Prometheus metrics
curl -s https://checkinos.io/metrics | head -n 10
```
