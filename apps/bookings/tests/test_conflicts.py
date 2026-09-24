"""Double-booking prevention — the core scheduling guarantee."""
import datetime as dt

import pytest

from apps.bookings.models import BookingStatus, Purpose
from apps.bookings.services import BookingService

pytestmark = pytest.mark.django_db


def T(h):
    return dt.time(h)


def test_overlapping_booking_is_a_conflict(world, today, make_booking):
    room = world["rooms"]["geo_small"]
    make_booking(room, 8, 10)                       # existing 08:00-10:00
    result = BookingService.check_availability(
        room=room, date=today, start=T(9), end=T(11), attendance=10, purpose=Purpose.LECTURE
    )
    assert result.ok is False
    assert result.conflict is not None


def test_adjacent_booking_is_not_a_conflict(world, today, make_booking):
    room = world["rooms"]["geo_small"]
    make_booking(room, 8, 10)
    # 10:00-12:00 starts exactly when the other ends — no overlap.
    result = BookingService.check_availability(
        room=room, date=today, start=T(10), end=T(12), attendance=10, purpose=Purpose.LECTURE
    )
    assert result.ok is True


def test_rejected_booking_does_not_block(world, today, make_booking):
    room = world["rooms"]["geo_small"]
    make_booking(room, 8, 10, status=BookingStatus.REJECTED)
    result = BookingService.check_availability(
        room=room, date=today, start=T(8), end=T(10), attendance=10, purpose=Purpose.LECTURE
    )
    assert result.ok is True                        # rejected slots free up


def test_capacity_exceeded_blocks(world, today):
    room = world["rooms"]["geo_small"]              # capacity 40
    result = BookingService.check_availability(
        room=room, date=today, start=T(8), end=T(10), attendance=120, purpose=Purpose.LECTURE
    )
    assert result.ok is False
    assert result.capacity_exceeded is True
    # Alternatives suggested must all seat at least 120.
    assert all(r.capacity >= 120 for r in result.alternatives)


def test_create_request_guards_against_conflict(world, today, make_booking):
    room = world["rooms"]["geo_small"]
    make_booking(room, 8, 10)
    with pytest.raises(ValueError):
        BookingService.create_request(
            room=room, date=today, start=T(9), end=T(11), purpose=Purpose.LECTURE,
            attendance=10, requester=None, requester_name="X",
        )
