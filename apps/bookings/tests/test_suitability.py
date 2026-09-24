"""Purpose -> suitability tag matching (multi-purpose rooms)."""
import datetime as dt

import pytest

from apps.bookings.models import Purpose
from apps.bookings.services import BookingService

pytestmark = pytest.mark.django_db


def T(h):
    return dt.time(h)


def test_meeting_room_rejects_examination(world, today):
    # law_mr is tagged only for Meetings, not Examinations.
    room = world["rooms"]["law_mr"]
    result = BookingService.check_availability(
        room=room, date=today, start=T(9), end=T(11), attendance=50, purpose=Purpose.EXAMINATION
    )
    assert result.ok is False
    assert result.unsuitable is True


def test_lecture_theatre_accepts_lecture(world, today):
    room = world["rooms"]["geo_small"]              # tagged Lectures
    result = BookingService.check_availability(
        room=room, date=today, start=T(9), end=T(11), attendance=30, purpose=Purpose.LECTURE
    )
    assert result.ok is True


def test_unsuitable_room_suggests_suitable_alternatives(world, today):
    room = world["rooms"]["law_mr"]                 # not exam-suitable
    result = BookingService.check_availability(
        room=room, date=today, start=T(9), end=T(11), attendance=100, purpose=Purpose.EXAMINATION
    )
    assert result.ok is False
    # Every alternative must actually be exam-suitable.
    for alt in result.alternatives:
        assert alt.suits("Examinations")
