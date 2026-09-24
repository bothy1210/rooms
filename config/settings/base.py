"""
Base settings shared by all environments.

Environment-specific files (development.py, production.py, test.py) import
everything from here with `from .base import *` and override as needed.
Secrets are read from the environment / .env — never hard-coded.
"""
from pathlib import Path

import environ

# ── Paths ──────────────────────────────────────────────────────────────
# BASE_DIR = the project root (the folder containing manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Environment ────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
# Read /etc/roomsys/.env in production, or ./.env in development, if present.
for candidate in (Path("/etc/roomsys/.env"), BASE_DIR / ".env"):
    if candidate.exists():
        environ.Env.read_env(str(candidate))
        break

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTITUTION_NAME = env("INSTITUTION_NAME", default="University of Zimbabwe")

# ── Applications ───────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Local apps — one per concept-note module. `core` must load first because
# the others depend on its organisational / physical hierarchy models.
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.rooms",
    "apps.usage",
    "apps.bookings",
    "apps.approvals",
    "apps.dashboards",
    "apps.notifications",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

# ── Middleware ─────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Captures the acting user so audit signals can record "who" (see apps.audit).
    "apps.audit.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Injects institution name, org tree and the current dashboard
                # scope into every template.
                "apps.core.context_processors.institution",
                "apps.core.context_processors.current_scope",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ───────────────────────────────────────────────────────────
# Native PostgreSQL, localhost only. Configured via DATABASE_URL in .env.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://roomsys:roomsys@127.0.0.1:5432/roomsys_db",
    )
}
# Reuse connections across requests instead of opening one per page view;
# health checks drop a connection PostgreSQL has closed before it is reused.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# ── Cache ──────────────────────────────────────────────────────────────
# Redis when REDIS_URL is set (shared by every Gunicorn worker — use this in
# production); otherwise a per-process memory cache, fine for development.
if env("REDIS_URL", default=""):
    CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "KEY_PREFIX": "roomsys",
    }}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Sessions are read on every request: serve them from the cache, keep the DB copy.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# How long dashboard/report figures may be served from the cache (seconds).
# Room and booking changes clear them straight away, so this only bounds staleness.
DASHBOARD_CACHE_SECONDS = env.int("DASHBOARD_CACHE_SECONDS", default=120)

# Rooms go back to Available when their booking ends. Cron runs the
# `refresh_room_status` command; page views also trigger it, at most this often.
ROOM_STATUS_AUTO_REFRESH = env.bool("ROOM_STATUS_AUTO_REFRESH", default=True)
ROOM_STATUS_REFRESH_SECONDS = env.int("ROOM_STATUS_REFRESH_SECONDS", default=60)

# ── Authentication ─────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # Enable to authenticate against the Omhare directory (see accounts/backends.py):
    # "apps.accounts.backends.OmhareLDAPBackend",
]

# Stale login forms redirect to a fresh login page instead of showing a 403.
CSRF_FAILURE_VIEW = "apps.accounts.views.csrf_failure"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboards:home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ───────────────────────────────────────────────
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

# ── Static & media ─────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

# ── Email ──────────────────────────────────────────────────────────────
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="roomsys@uz.ac.zw")

# ── Defaults ───────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
