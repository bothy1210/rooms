"""Production settings — DEBUG off, HTTPS enforced, SMTP email."""
from .base import *  # noqa: F401,F403

DEBUG = False

# Render sets its public hostname (e.g. roomsys.onrender.com) in the environment.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")  # noqa: F405
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)  # noqa: F405
    CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"]

# ── SMTP email (credentials from .env) ─────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.uz.ac.zw")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405

# ── Security headers (system behind Nginx + TLS) ───────────────────────
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)  # noqa: F405
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ── Logging to file (rotated by logrotate on the server) ───────────────
import os as _os

_LOG_FILE = env("LOG_FILE", default="/var/log/roomsys/app.log")  # noqa: F405
# Fall back to console logging if the log directory isn't writable
# (e.g. during collectstatic in CI, or before the dir is provisioned).
_log_dir = _os.path.dirname(_LOG_FILE)
_use_file = _os.path.isdir(_log_dir) and _os.access(_log_dir, _os.W_OK)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": _LOG_FILE,
        } if _use_file else {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "root": {"handlers": ["file"], "level": "INFO"},
}
