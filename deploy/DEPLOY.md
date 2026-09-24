# Deployment Runbook — UZ Room Inventory & Usage Monitoring System

Target: a single **Ubuntu Server 24.04 LTS** host. **No Docker.** Native
PostgreSQL, Gunicorn under systemd, Nginx as the reverse proxy.

Conventions used below:
- App code: `/opt/roomsys`
- Virtualenv: `/opt/roomsys/venv`
- Secrets: `/etc/roomsys/.env` (mode 600)
- Static: `/var/roomsys/static` · Media: `/var/roomsys/media`
- Service user: `roomsys`

---

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential \
    postgresql postgresql-contrib nginx git \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev  # WeasyPrint deps
```

## 2. Service user & directories

```bash
sudo useradd --system --home /opt/roomsys --shell /usr/sbin/nologin roomsys
sudo mkdir -p /opt/roomsys /var/roomsys/static /var/roomsys/media /var/log/roomsys /etc/roomsys
sudo chown -R roomsys:www-data /var/roomsys /var/log/roomsys
```

## 3. PostgreSQL (native — no Docker)

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE roomsys WITH LOGIN PASSWORD 'change-me-strong';
CREATE DATABASE roomsys_db OWNER roomsys;
ALTER ROLE roomsys SET client_encoding TO 'utf8';
ALTER ROLE roomsys SET timezone TO 'Africa/Harare';
SQL
```

PostgreSQL listens on `127.0.0.1` by default — leave it that way so the database
is never exposed to the network.

## 4. Application code & virtualenv

```bash
sudo -u roomsys git clone <your-repo-url> /opt/roomsys
cd /opt/roomsys
sudo -u roomsys python3 -m venv venv
sudo -u roomsys ./venv/bin/pip install -r requirements.txt
```

## 5. Environment file

```bash
sudo cp /opt/roomsys/.env.example /etc/roomsys/.env
sudo nano /etc/roomsys/.env        # set SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, SMTP
sudo chmod 600 /etc/roomsys/.env
sudo chown roomsys:roomsys /etc/roomsys/.env
```

Generate a secret key:

```bash
./venv/bin/python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

## 6. Migrate, collect static, create the first administrator

```bash
cd /opt/roomsys
export DJANGO_SETTINGS_MODULE=config.settings.production
sudo -u roomsys ./venv/bin/python manage.py migrate
sudo -u roomsys STATIC_ROOT=/var/roomsys/static ./venv/bin/python manage.py collectstatic --noinput
sudo -u roomsys ./venv/bin/python manage.py createsuperuser   # use an R-number
```

## 7. Gunicorn under systemd

```bash
sudo cp deploy/systemd/roomsys.socket  /etc/systemd/system/
sudo cp deploy/systemd/roomsys.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now roomsys.socket
sudo systemctl enable --now roomsys
sudo systemctl status roomsys           # should be active (running)
```

## 8. Nginx

```bash
sudo cp deploy/nginx/roomsys.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/roomsys.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

TLS certificate (Let's Encrypt):

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rooms.uz.ac.zw
```

## 9. Scheduled jobs

```bash
sudo cp deploy/cron/roomsys.cron /etc/cron.d/roomsys
sudo chmod 644 /etc/cron.d/roomsys
```

## 10. Backups

```bash
sudo chmod +x scripts/backup_db.sh scripts/restore_db.sh
# The nightly backup line is already in the cron file (step 9).
```

---

## Upgrades (after a code change)

```bash
cd /opt/roomsys
sudo -u roomsys git pull
sudo -u roomsys ./venv/bin/pip install -r requirements.txt
sudo -u roomsys ./venv/bin/python manage.py migrate
sudo -u roomsys STATIC_ROOT=/var/roomsys/static ./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart roomsys
```

## Health checks

```bash
systemctl status roomsys nginx postgresql
journalctl -u roomsys -n 50 --no-pager      # application logs
tail -f /var/log/roomsys/cron.log           # scheduled-job logs
```

## Optional: Omhare directory integration

To let users sign in with their existing Omhare R-number, enable an LDAP/SSO
backend in `config/settings/production.py` and
`apps/accounts/backends.py::OmhareLDAPBackend`, then install `django-auth-ldap`
(already listed, commented, in `requirements.txt`). Until then, accounts are
self-contained and created via the Django admin or `createsuperuser`.
