"""
Room signals -> audit trail.

We capture the previous status before a save and, if it changed, write an audit
entry afterwards. New-room creation (verification) is also logged. This keeps
§7.8 (audit trail) automatic — no view has to remember to log.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.audit.services import log_change
from apps.rooms.models import Room


@receiver(pre_save, sender=Room)
def _remember_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Room.objects.get(pk=instance.pk).status
        except Room.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Room)
def _log_room_change(sender, instance, created, **kwargs):
    if created:
        log_change("Room registered", f"{instance.code} — {instance.name}", "—", "Verified · Active")
        return
    old = getattr(instance, "_old_status", None)
    if old is not None and old != instance.status:
        log_change(
            "Status change",
            f"{instance.code} — {instance.name}",
            dict(Room._meta.get_field("status").choices).get(old, old),
            instance.get_status_display(),
        )
        # Append to the room's usage history as well.
        from apps.usage.services import record_usage
        from apps.audit.middleware import get_current_user
        record_usage(instance, instance.status, changed_by=get_current_user())
