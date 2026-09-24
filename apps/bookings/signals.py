"""Booking signals -> audit trail."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.audit.services import log_change
from apps.bookings.models import Booking


@receiver(post_save, sender=Booking)
def _log_booking(sender, instance, created, **kwargs):
    if created:
        log_change("Booking submitted", f"BK-{instance.pk} - {instance.room.code}", "-", "Pending approval")
