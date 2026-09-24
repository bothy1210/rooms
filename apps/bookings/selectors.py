"""
Find-a-Venue selector.

Capacity-first, university-wide venue discovery: given how many people need
accommodating (and optionally a purpose, date and time window), return every
suitable, free room across ALL faculties and departments, ranked by best
capacity fit. Ownership never hides a room — it only decides who approves.
"""
from django.db.models import Q

from apps.bookings.models import PURPOSE_TO_TAG, Purpose
from apps.bookings.services import BookingService
from apps.rooms.models import UNAVAILABLE_STATUSES, Room


def find_venues_by_capacity(*, attendance, purpose=Purpose.MEETING, date=None,
                            start=None, end=None, limit=20):
    """Return rooms that can accommodate `attendance` for `purpose`, free at the
    given time (if a time window is supplied), ranked smallest-fit first."""
    required_tag = PURPOSE_TO_TAG.get(purpose)
    qs = (
        Room.objects.exclude(status__in=UNAVAILABLE_STATUSES)
        .filter(capacity__gte=attendance)
        .select_related("building", "department", "department__faculty", "room_type")
    )
    if required_tag:
        # A room tagged for some purposes is limited to those; one with no tags
        # recorded is not restricted, so it stays in the results.
        qs = qs.filter(Q(suitability__name__iexact=required_tag) | Q(suitability__isnull=True)).distinct()
    qs = qs.order_by("capacity")

    if not (date and start and end):
        return list(qs[:limit])

    # Time window supplied — exclude rooms with a clashing booking.
    free = []
    for room in qs:
        if not BookingService.find_conflicts(room, date, start, end).exists():
            free.append(room)
        if len(free) >= limit:
            break
    return free
