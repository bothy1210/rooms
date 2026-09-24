"""Helper to write audit entries, resolving the acting user from middleware."""
from apps.audit.middleware import get_current_user
from apps.audit.models import AuditLog


def log_change(action, target, previous="", new="", user=None):
    AuditLog.objects.create(
        user=user or get_current_user(),
        action=action,
        target=str(target),
        previous_value=str(previous),
        new_value=str(new),
    )
