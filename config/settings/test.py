"""Test settings — fast password hashing, local-memory email."""
from .base import *  # noqa: F401,F403

DEBUG = False

# Speed up tests: use the fast (insecure) hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Allow tests to run against SQLite when Postgres isn't available locally,
# by setting TEST_DATABASE_URL=sqlite:// in the environment. Defaults to the
# configured Postgres DATABASE_URL otherwise.
DATABASES = {"default": env.db("TEST_DATABASE_URL", default=env("DATABASE_URL", default="sqlite://:memory:"))}  # noqa: F405

SECURE_SSL_REDIRECT = False
