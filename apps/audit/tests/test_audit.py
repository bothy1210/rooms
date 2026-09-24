"""Tests for the audit logging service and its middleware-resolved user."""
import pytest

from apps.audit.middleware import _local
from apps.audit.models import AuditLog
from apps.audit.services import log_change
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_log_change_creates_entry():
    log_change("Status change", "UZ-LT-101", "Available", "Booked")
    entry = AuditLog.objects.get()
    assert entry.action == "Status change"
    assert entry.previous_value == "Available"
    assert entry.new_value == "Booked"


def test_log_change_uses_explicit_user():
    user = User.objects.create_user("R1", full_name="Actor")
    log_change("Room registered", "UZ-LT-102", user=user)
    assert AuditLog.objects.get().user == user


def test_log_change_falls_back_to_current_user(settings):
    """When no user is passed, the middleware-stored current user is used."""
    user = User.objects.create_user("R2", full_name="Middleware User")
    _local.user = user
    try:
        log_change("Status change", "UZ-LT-103", "Available", "Closed")
        assert AuditLog.objects.get().user == user
    finally:
        _local.user = None
