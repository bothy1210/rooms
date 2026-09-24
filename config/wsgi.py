"""WSGI config — Gunicorn's entry point in production.

The systemd EnvironmentFile sets DJANGO_SETTINGS_MODULE=config.settings.production.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_wsgi_application()
