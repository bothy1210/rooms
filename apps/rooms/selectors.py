"""
Room read queries (selectors).

All room list/search logic lives here so views stay thin and the same filters
power the inventory page, the dashboard and any future API.
"""
from django.db.models import Q

from apps.core.selectors import apply_room_scope
from apps.rooms.models import UNAVAILABLE_STATUSES, Room


def base_rooms():
    """Rooms with their related objects pre-fetched (avoids N+1 queries)."""
    return (
        Room.objects.select_related("building", "floor", "department", "department__faculty", "room_type")
        .prefetch_related("suitability", "equipment")
    )


def search_rooms(*, scope=None, query="", building_id=None, room_type_id=None,
                 status="", min_capacity=0):
    """Filter the inventory. `scope` (a ResolvedScope) restricts to dept/faculty/uni."""
    qs = base_rooms()
    if scope is not None:
        qs = apply_room_scope(qs, scope)
    if query:
        qs = qs.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(building__name__icontains=query)
        )
    if building_id:
        qs = qs.filter(building_id=building_id)
    if room_type_id:
        qs = qs.filter(room_type_id=room_type_id)
    if status == "unavailable":
        qs = qs.filter(status__in=UNAVAILABLE_STATUSES)
    elif status:
        qs = qs.filter(status=status)
    if min_capacity:
        qs = qs.filter(capacity__gte=min_capacity)
    return qs
