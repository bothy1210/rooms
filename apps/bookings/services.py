"""
Booking business rules.

BookingService is the single source of truth for whether a room can be booked:
time-overlap conflict detection, capacity check, and purpose→suitability
matching — mirroring the prototype's conflict checker. It also suggests
alternatives (university-wide, capacity-ranked) when a request fails.

Everything here is pure query logic with no view dependencies, so it is unit
testable and reusable by the API and the Find-a-Venue feature.
"""
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q

from apps.bookings.models import (
    PURPOSE_TO_TAG,
    Booking,
    BookingStatus,
)
from apps.rooms.models import UNAVAILABLE_STATUSES, Room

# Statuses that occupy a room's time slot.
BLOCKING_STATUSES = [BookingStatus.PENDING, BookingStatus.APPROVED]


@dataclass
class AvailabilityResult:
    ok: bool
    conflict: Booking | None = None
    capacity_exceeded: bool = False
    unsuitable: bool = False
    room_capacity: int = 0
    required_tag: str | None = None
    alternatives: list[Room] = field(default_factory=list)


class BookingService:
    @staticmethod
    def _overlaps(qs, start, end):
        # Two intervals overlap iff start < other_end AND other_start < end.
        return qs.filter(start_time__lt=end, end_time__gt=start)

    @classmethod
    def find_conflicts(cls, room, date, start, end, exclude_id=None):
        qs = Booking.objects.filter(room=room, date=date, status__in=BLOCKING_STATUSES)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        return cls._overlaps(qs, start, end)

    @classmethod
    def check_availability(cls, *, room, date, start, end, attendance=0, purpose=None) -> AvailabilityResult:
        """Full pre-booking check: conflict + capacity + suitability."""
        required_tag = PURPOSE_TO_TAG.get(purpose) if purpose else None
        conflict = cls.find_conflicts(room, date, start, end).first()
        capacity_exceeded = attendance > room.capacity if attendance else False
        # Only a room that carries suitability tags is restricted by them.
        unsuitable = (bool(required_tag) and room.suitability.exists()
                      and not room.suits(required_tag))

        if conflict or capacity_exceeded or unsuitable:
            return AvailabilityResult(
                ok=False,
                conflict=conflict,
                capacity_exceeded=capacity_exceeded,
                unsuitable=unsuitable,
                room_capacity=room.capacity,
                required_tag=required_tag,
                alternatives=cls.suggest_alternatives(
                    room, date, start, end, attendance, required_tag
                ),
            )
        return AvailabilityResult(ok=True, room_capacity=room.capacity, required_tag=required_tag)

    @classmethod
    def suggest_alternatives(cls, room, date, start, end, attendance=0, required_tag=None, limit=4):
        """University-wide, capacity-ranked alternatives free at that time."""
        qs = (
            Room.objects.exclude(pk=room.pk)
            .exclude(status__in=UNAVAILABLE_STATUSES)
            .select_related("building", "department")
        )
        if attendance:
            qs = qs.filter(capacity__gte=attendance)
        if required_tag:
            # Untagged rooms carry no restriction, so they remain candidates.
            qs = qs.filter(Q(suitability__name__iexact=required_tag) | Q(suitability__isnull=True)).distinct()
        qs = qs.order_by("capacity")  # best-fit first (smallest that still fits)
        result = []
        for candidate in qs:
            if not cls.find_conflicts(candidate, date, start, end).exists():
                result.append(candidate)
            if len(result) >= limit:
                break
        return result

    @classmethod
    @transaction.atomic
    def create_request(cls, *, room, date, start, end, purpose, attendance,
                       requester, requester_name="", requester_dept="", equipment_note="") -> Booking:
        """Create a booking after a successful availability check.

        Raises ValueError if the slot is not actually free (guards against a
        race between check and submit).
        """
        check = cls.check_availability(
            room=room, date=date, start=start, end=end, attendance=attendance, purpose=purpose
        )
        if not check.ok:
            raise ValueError("Room is not available for the requested slot.")
        return Booking.objects.create(
            room=room,
            requester=requester,
            requester_name=requester_name or (requester.full_name if requester else ""),
            requester_dept=requester_dept,
            purpose=purpose,
            date=date,
            start_time=start,
            end_time=end,
            attendance=attendance or 0,
            equipment_note=equipment_note,
            status=BookingStatus.PENDING,
        )
