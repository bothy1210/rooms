# Centralised Room Inventory & Usage Monitoring System

University of Zimbabwe — part of the Omhare University Information System family.

Django 5 · PostgreSQL 16 · Bootstrap 5 + HTMX + Alpine.js · Gunicorn + Nginx + systemd (no Docker).

See **ARCHITECTURE.md** for the full system design, deployment topology and data model.

## Local development

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # then edit DATABASE_URL, SECRET_KEY, etc.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The dev server uses `config.settings.development`. Production uses
`config.settings.production` (set via the systemd EnvironmentFile).

## Project layout

```
config/     project settings (split: base / development / production / test)
apps/       business modules — one Django app per concept-note module
templates/  server-rendered HTML (Omhare-themed)
static/     css / js / images
deploy/     Nginx, systemd, gunicorn, cron — no-Docker deployment
```

## Running tests

```bash
pytest
```
