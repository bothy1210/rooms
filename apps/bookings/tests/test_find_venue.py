"""Cross-faculty, capacity-first venue discovery."""
import datetime as dt

import pytest

from apps.bookings.models import Purpose
from apps.bookings.selectors import find_venues_by_capacity

pytestmark = pytest.mark.django_db


def T(h):
    return dt.time(h)


def test_search_returns_rooms_across_faculties(world):
    # Need 180 seats for a meeting: geo_big (200) and law_mr (250) qualify;
    # they belong to DIFFERENT faculties — ownership must not hide them.
    venues = find_venues_by_capacity(attendance=180, purpose=Purpose.MEETING)
    codes = {v.code for v in venues}
    assert "UZ-LT-102" in codes                     # Geoinformatics, 200
    assert "UZ-MR-101" in codes                     # Law, 250
    assert "UZ-LT-101" not in codes                 # only 40 seats


def test_results_ranked_by_best_capacity_fit(world):
    venues = find_venues_by_capacity(attendance=180, purpose=Purpose.MEETING)
    caps = [v.capacity for v in venues]
    assert caps == sorted(caps)                     # smallest-that-fits first


def test_time_window_excludes_clashing_rooms(world, today, make_booking):
    from apps.bookings.models import BookingStatus, Purpose as P
    # Block geo_big 09:00-11:00.
    make_booking(world["rooms"]["geo_big"], 9, 11, status=BookingStatus.APPROVED, purpose=P.MEETING)
    venues = find_venues_by_capacity(
        attendance=180, purpose=Purpose.MEETING, date=today, start=T(9), end=T(10)
    )
    codes = {v.code for v in venues}
    assert "UZ-LT-102" not in codes                 # busy at that time
    assert "UZ-MR-101" in codes                     # still free


def test_no_results_when_nothing_large_enough(world):
    venues = find_venues_by_capacity(attendance=5000, purpose=Purpose.MEETING)
    assert venues == []
