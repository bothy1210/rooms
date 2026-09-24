"""
Dashboard assembly service.

Bundles the individual selectors into a single payload for a given user + scope,
so the view (and the export builders) request the whole dashboard in one call
and stay consistent with each other.
"""
from apps.bookings.models import Booking, BookingStatus
from apps.core.selectors import apply_room_scope
from apps.core.services import ScopeService
from apps.dashboards import selectors
from apps.dashboards.cache import cached_for_scope

DASHBOARD_PENDING_LIMIT = 5


def build_dashboard(user, requested_scope=None) -> dict:
    scope = ScopeService.resolve(user, requested_scope)

    # Scope the bookings shown on the dashboard to rooms in the current scope.
    scoped_rooms = apply_room_scope(
        __import__("apps.rooms.models", fromlist=["Room"]).Room.objects.all(), scope
    )
    pending = (
        Booking.objects.filter(status=BookingStatus.PENDING, room__in=scoped_rooms)
        .select_related("room", "room__department")
    )
    upcoming = (
        Booking.objects.filter(status=BookingStatus.APPROVED, room__in=scoped_rooms)
        .select_related("room").order_by("date", "start_time")[:5]
    )

    return {
        "scope": scope,
        "available_scopes": ScopeService.available_scopes(user),
        # Aggregates are the same for everyone in a scope: shared via the cache.
        "stats": cached_for_scope("stats", scope, lambda: selectors.status_counts(scope)),
        "by_building": cached_for_scope("by_building", scope, lambda: selectors.utilisation_by_building(scope)),
        "by_type": cached_for_scope("by_type", scope, lambda: selectors.utilisation_by_type(scope)),
        # The card lists the oldest few; the full queue is on the Approvals page.
        "pending": pending.order_by("date", "start_time")[:DASHBOARD_PENDING_LIMIT],
        "pending_total": pending.count(),
        "upcoming": upcoming,
    }
