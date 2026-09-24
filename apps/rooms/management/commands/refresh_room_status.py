"""Put rooms back to Available once their booking time has passed.

Run every few minutes from cron (see deploy/cron/roomsys.cron). The dashboard
and room list also trigger this, so the figures are right between cron runs.
"""
from django.core.management.base import BaseCommand

from apps.rooms.services import RoomStatusService


class Command(BaseCommand):
    help = "Refresh live room statuses (Available / Booked / In use) from today's bookings."

    def handle(self, *args, **options):
        result = RoomStatusService.refresh_live_statuses()
        self.stdout.write(
            f"Rooms updated: {result['rooms_changed']}; "
            f"past bookings marked completed: {result['bookings_completed']}."
        )
