"""
Dashboard read queries.

All aggregation lives here so the dashboard, the reports pages and the export
builders share exactly one definition of "utilisation". Every query accepts a
ResolvedScope so the numbers match whatever scope the user has selected
(My Department / My Faculty / University-wide).
"""
from django.db.models import Count, Q, Sum

from apps.core.selectors import apply_room_scope
from apps.rooms.models import UNAVAILABLE_STATUSES, Room, RoomStatus


def _scoped(scope):
    qs = Room.objects.select_related("department", "department__faculty", "building", "room_type")
    return apply_room_scope(qs, scope) if scope is not None else qs


def status_counts(scope=None) -> dict:
    """Counts used by the stat cards + donut, within the scope."""
    # One aggregate query rather than a separate COUNT per card.
    counts = _scoped(scope).aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(status=RoomStatus.AVAILABLE)),
        in_use=Count("id", filter=Q(status=RoomStatus.IN_USE)),
        booked=Count("id", filter=Q(status=RoomStatus.BOOKED)),
        unavailable=Count("id", filter=Q(status__in=UNAVAILABLE_STATUSES)),
        capacity=Sum("capacity"),
    )
    total, in_use, booked = counts["total"], counts["in_use"], counts["booked"]
    available, unavailable = counts["available"], counts["unavailable"]
    capacity = counts["capacity"] or 0
    utilisation = round((in_use + booked) / total * 100) if total else 0
    return {
        "total": total,
        "available": available,
        "in_use": in_use,
        "booked": booked,
        "unavailable": unavailable,
        "capacity": capacity,
        "utilisation": utilisation,
    }


def utilisation_by(dimension, scope=None):
    """Group rooms by a dimension and return utilisation per group.

    `dimension` is a related field path, e.g. 'building__name',
    'department__name', 'room_type__name'.
    """
    qs = _scoped(scope)
    rows = (
        qs.values(dimension)
        .annotate(
            rooms=Count("id"),
            capacity=Sum("capacity"),
            used=Count("id", filter=Q(status__in=[RoomStatus.IN_USE, RoomStatus.BOOKED])),
            available=Count("id", filter=Q(status=RoomStatus.AVAILABLE)),
        )
        .order_by("-rooms")
    )
    result = []
    for r in rows:
        pct = round(r["used"] / r["rooms"] * 100) if r["rooms"] else 0
        result.append({
            "label": r[dimension],
            "rooms": r["rooms"],
            "capacity": r["capacity"] or 0,
            "used": r["used"],
            "available": r["available"],
            "utilisation": pct,
        })
    return result


def utilisation_by_building(scope=None):
    return utilisation_by("building__name", scope)


def utilisation_by_department(scope=None):
    return utilisation_by("department__name", scope)


def utilisation_by_type(scope=None):
    return utilisation_by("room_type__name", scope)


def most_used_rooms(scope=None, limit=5):
    """Rooms ranked by number of (non-rejected/cancelled) bookings."""
    qs = _scoped(scope).annotate(
        booking_count=Count("bookings", filter=~Q(bookings__status__in=["rejected", "cancelled"]))
    ).order_by("-booking_count")[:limit]
    return [{"room": r, "bookings": r.booking_count} for r in qs]


def least_used_rooms(scope=None, limit=5):
    qs = _scoped(scope).annotate(
        booking_count=Count("bookings", filter=~Q(bookings__status__in=["rejected", "cancelled"]))
    ).order_by("booking_count")[:limit]
    return [{"room": r, "bookings": r.booking_count} for r in qs]
