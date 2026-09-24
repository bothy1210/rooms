"""Clear cached dashboard figures whenever a room or booking changes."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.bookings.models import Booking
from apps.dashboards.cache import invalidate
from apps.rooms.models import Room


@receiver([post_save, post_delete], sender=Room)
@receiver([post_save, post_delete], sender=Booking)
def clear_dashboard_cache(sender, **kwargs):
    invalidate()
