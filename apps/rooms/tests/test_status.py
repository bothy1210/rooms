"""
Live status: a status set by hand survives the diary refresh until the diary
next moves on (a booking starts or ends).
"""
import datetime as dt

import pytest
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus, Purpose
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.rooms.services import RoomStatusService

pytestmark = pytest.mark.django_db

DAY = dt.date(2026, 9, 28)


@pytest.fixture
def clock(monkeypatch):
    """Pin 'now' to a moment on DAY; call clock(h, m) to move it."""
    def set_time(hour, minute=0):
        moment = timezone.make_aware(dt.datetime.combine(DAY, dt.time(hour, minute)))
        monkeypatch.setattr(timezone, "now", lambda: moment)
    set_time(10, 30)
    return set_time


@pytest.fixture
def room():
    campus = Campus.objects.create(name="Main Campus", code="MC")
    building = Building.objects.create(campus=campus, name="Science", code="SCI")
    floor = Floor.objects.create(building=building, name="Ground", level=0)
    fac = Faculty.objects.create(name="Faculty of Science", code="SCI")
    dept = Department.objects.create(faculty=fac, name="Computer Science", code="CS")
    lt = RoomType.objects.create(name="Lecture Theatre", code="LT")
    return Room.objects.create(code="UZ-LT-101", name="LT 1", building=building, floor=floor,
                               department=dept, room_type=lt, capacity=100)


def book(room, start, end):
    return Booking.objects.create(room=room, requester_name="Test", purpose=Purpose.LECTURE, date=DAY,
                                  start_time=dt.time(start), end_time=dt.time(end),
                                  attendance=10, status=BookingStatus.APPROVED)


def status_of(room):
    room.refresh_from_db()
    return room.status


def test_refresh_follows_diary_without_manual_change(clock, room):
    book(room, 10, 12)
    RoomStatusService.refresh_live_statuses()
    assert status_of(room) == RoomStatus.IN_USE


def test_manual_status_survives_refresh(clock, room):
    book(room, 10, 12)
    RoomStatusService.refresh_live_statuses()
    RoomStatusService.update_status(room, RoomStatus.AVAILABLE)   # lecture cancelled on the day

    RoomStatusService.refresh_live_statuses()
    assert status_of(room) == RoomStatus.AVAILABLE


def test_diary_takes_over_again_at_next_booking(clock, room):
    book(room, 10, 12)
    book(room, 14, 16)
    RoomStatusService.update_status(room, RoomStatus.AVAILABLE)

    clock(14, 5)   # the afternoon booking has started since the manual change
    RoomStatusService.refresh_live_statuses()
    assert status_of(room) == RoomStatus.IN_USE


def test_manual_unavailable_status_is_never_overridden(clock, room):
    book(room, 10, 12)
    RoomStatusService.update_status(room, RoomStatus.MAINTENANCE)
    room.refresh_from_db()
    assert room.status_set_at is None

    RoomStatusService.refresh_live_statuses()
    assert status_of(room) == RoomStatus.MAINTENANCE
