"""Usage service - append a usage-log entry whenever a room's status changes."""
from apps.usage.models import UsageLog


def record_usage(room, status, changed_by=None, note=""):
    return UsageLog.objects.create(room=room, status=status, changed_by=changed_by, note=note)
