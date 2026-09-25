"""
Room registration & status services.

RoomRegistrationService encodes the Draft -> Verify -> Official Code workflow
the client asked for, so rooms enter the inventory in a controlled way (no
duplicates, no ghost rooms, consistent codes). Business rules live here, never
in views, so they can be reused by the API and tested in isolation.
"""
from collections import defaultdict
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.rooms.models import (
    DraftStatus,
    Room,
    RoomDraft,
    RoomStatus,
)


class RoomRegistrationError(Exception):
    """Raised when a registration step is invalid (e.g. verifying twice)."""


class RoomRegistrationService:
    """Draft -> Verify -> issue official code."""

    @staticmethod
    @transaction.atomic
    def submit_draft(*, name, building, floor, department, room_type, capacity,
                     submitted_by, accessibility="", remarks="", photo=None) -> RoomDraft:
        """A department submits a proposed room. It is NOT bookable yet."""
        if capacity is None or capacity < 1:
            raise RoomRegistrationError("Capacity must be a positive number.")
        return RoomDraft.objects.create(
            name=name.strip(),
            building=building,
            floor=floor,
            department=department,
            room_type=room_type,
            capacity=capacity,
            accessibility=accessibility,
            remarks=remarks,
            photo=photo,
            submitted_by=submitted_by,
            status=DraftStatus.DRAFT,
        )

    @staticmethod
    def _next_code(room_type) -> str:
        """Generate the next official code for a room type, e.g. UZ-LT-101.

        Numbers continue from the highest existing code of that type so codes
        never collide, even across departments.
        """
        prefix = f"UZ-{room_type.code}-"
        existing = (
            Room.objects.filter(code__startswith=prefix)
            .values_list("code", flat=True)
        )
        max_seq = 100
        for code in existing:
            tail = code.rsplit("-", 1)[-1]
            if tail.isdigit():
                max_seq = max(max_seq, int(tail))
        return f"{prefix}{max_seq + 1}"

    @classmethod
    @transaction.atomic
    def verify(cls, draft: RoomDraft, *, verified_by, suitability=None, equipment=None) -> Room:
        """
        Central administration verifies a draft: a Room is created with an
        official code and the draft is marked Verified. Only now is it bookable.
        """
        if draft.status != DraftStatus.DRAFT:
            raise RoomRegistrationError(
                f"Draft '{draft.name}' is already {draft.get_status_display()}."
            )

        room = Room.objects.create(
            code=cls._next_code(draft.room_type),
            name=draft.name,
            building=draft.building,
            floor=draft.floor,
            department=draft.department,
            room_type=draft.room_type,
            capacity=draft.capacity,
            accessibility=draft.accessibility,
            remarks=draft.remarks,
            # The uploaded file stays where it is; the room points at the same one.
            photo=draft.photo.name or None,
            status=RoomStatus.AVAILABLE,
        )
        # Default suitability from the room type if none supplied.
        if suitability:
            room.suitability.set(suitability)
        if equipment:
            room.equipment.set(equipment)

        draft.status = DraftStatus.VERIFIED
        draft.verified_by = verified_by
        draft.verified_at = timezone.now()
        draft.resulting_room = room
        draft.save(update_fields=["status", "verified_by", "verified_at", "resulting_room", "updated_at"])
        return room

    @staticmethod
    @transaction.atomic
    def reject(draft: RoomDraft, *, verified_by) -> RoomDraft:
        if draft.status != DraftStatus.DRAFT:
            raise RoomRegistrationError("Only pending drafts can be rejected.")
        draft.status = DraftStatus.REJECTED
        draft.verified_by = verified_by
        draft.verified_at = timezone.now()
        draft.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        return draft


class RoomStatusService:
    """Update a room's live status (subject to the caller's scope, checked in the view)."""

    @staticmethod
    def update_status(room: Room, new_status: str) -> tuple[str, str]:
        """Change status, returning (old, new). The audit signal records the rest."""
        if new_status not in RoomStatus.values:
            raise RoomRegistrationError(f"Unknown status '{new_status}'.")
        old = room.status
        room.status = new_status
        # A hand-set diary status is kept until the diary next moves on.
        room.status_set_at = timezone.now() if new_status in RoomStatusService.AUTO_STATUSES else None
        room.save(update_fields=["status", "status_set_at", "updated_at"])
        return old, new_status

    # Statuses the system maintains from the booking diary. The others
    # (maintenance, cleaning, closed) are set by a person and are left alone.
    AUTO_STATUSES = {RoomStatus.AVAILABLE, RoomStatus.BOOKED, RoomStatus.IN_USE}

    @classmethod
    def status_from_diary(cls, room, bookings) -> str:
        """AVAILABLE / BOOKED / IN_USE for a room, given today's approved bookings."""
        now = timezone.localtime()
        today, clock = now.date(), now.time()
        for booking in bookings:
            if booking.date == today and booking.start_time <= clock < booking.end_time:
                return RoomStatus.IN_USE
        if any(b.date == today and b.start_time > clock for b in bookings):
            return RoomStatus.BOOKED
        return RoomStatus.AVAILABLE

    @staticmethod
    def last_diary_change(bookings):
        """The latest moment today a booking started or ended (midnight if none yet)."""
        now = timezone.localtime()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        moments = [
            timezone.make_aware(datetime.combine(b.date, t), now.tzinfo)
            for b in bookings for t in (b.start_time, b.end_time)
            if b.date == now.date()
        ]
        return max([m for m in moments if m <= now] + [midnight])

    @classmethod
    @transaction.atomic
    def refresh_live_statuses(cls) -> dict:
        """Put rooms back to Available once their booking has finished.

        Run from the `refresh_room_status` command (cron) and opportunistically
        when someone opens the dashboard or the room list.
        """
        from apps.bookings.models import Booking, BookingStatus

        today = timezone.localdate()
        todays = list(
            Booking.objects.filter(status=BookingStatus.APPROVED, date=today)
            .only("room_id", "date", "start_time", "end_time")
        )
        by_room = defaultdict(list)
        for booking in todays:
            by_room[booking.room_id].append(booking)

        changed = 0
        for room in Room.objects.filter(status__in=cls.AUTO_STATUSES):
            bookings = by_room.get(room.pk, ())
            # Respect a status someone set by hand since the diary last changed.
            if room.status_set_at and room.status_set_at >= cls.last_diary_change(bookings):
                continue
            wanted = cls.status_from_diary(room, bookings)
            if wanted != room.status:
                room.status = wanted
                room.save(update_fields=["status", "updated_at"])   # signals keep the dashboard in step
                changed += 1

        # An approved booking whose day has passed is done with.
        completed = (
            Booking.objects.filter(status=BookingStatus.APPROVED, date__lt=today)
            .update(status=BookingStatus.COMPLETED)
        )
        return {"rooms_changed": changed, "bookings_completed": completed}

    @classmethod
    def refresh_live_statuses_throttled(cls):
        """As above, but at most once every ROOM_STATUS_REFRESH_SECONDS across
        all workers, so page views stay cheap."""
        if not getattr(settings, "ROOM_STATUS_AUTO_REFRESH", True):
            return None
        seconds = getattr(settings, "ROOM_STATUS_REFRESH_SECONDS", 60)
        if not cache.add("rooms:status-refresh", 1, timeout=seconds):
            return None
        return cls.refresh_live_statuses()
