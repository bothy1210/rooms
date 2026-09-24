"""Shared fixtures for booking tests."""
import datetime as dt

import pytest

from apps.bookings.models import Booking, BookingStatus, Purpose
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.rooms.models import Room, RoomStatus, RoomType, SuitabilityTag


@pytest.fixture
def world(db):
    campus = Campus.objects.create(name="Main", code="MC")
    b = Building.objects.create(campus=campus, name="Science", code="SCI")
    f = Floor.objects.create(building=b, name="Ground", level=0)

    sci = Faculty.objects.create(name="Faculty of Science", code="SCI")
    law_fac = Faculty.objects.create(name="Faculty of Law", code="LAW")
    geo = Department.objects.create(faculty=sci, name="Geoinformatics", code="GIS")
    law = Department.objects.create(faculty=law_fac, name="Law", code="LAW")

    lt = RoomType.objects.create(name="Lecture room", code="LT")
    mr = RoomType.objects.create(name="Meeting room", code="MR")

    # get_or_create: these tags also ship as migration data (rooms.0003).
    tag_lecture, _ = SuitabilityTag.objects.get_or_create(name="Lectures")
    tag_meeting, _ = SuitabilityTag.objects.get_or_create(name="Meetings")
    tag_exam, _ = SuitabilityTag.objects.get_or_create(name="Examinations")

    def mk(code, dept, cap, rtype, tags, status=RoomStatus.AVAILABLE):
        r = Room.objects.create(code=code, name=code, building=b, floor=f,
                                department=dept, room_type=rtype, capacity=cap, status=status)
        r.suitability.set(tags)
        return r

    rooms = {
        "geo_small": mk("UZ-LT-101", geo, 40, lt, [tag_lecture]),
        "geo_big": mk("UZ-LT-102", geo, 200, lt, [tag_lecture, tag_meeting]),
        "law_mr": mk("UZ-MR-101", law, 250, mr, [tag_meeting]),
        "law_lt": mk("UZ-LT-103", law, 300, lt, [tag_lecture, tag_exam]),
    }
    return dict(rooms=rooms, geo=geo, law=law, sci=sci,
                tags=dict(lecture=tag_lecture, meeting=tag_meeting, exam=tag_exam))


@pytest.fixture
def today():
    return dt.date.today()


def T(h, m=0):
    return dt.time(h, m)


@pytest.fixture
def make_booking(today):
    def _make(room, start_h, end_h, status=BookingStatus.APPROVED, purpose=Purpose.LECTURE):
        return Booking.objects.create(
            room=room, requester_name="Test", purpose=purpose, date=today,
            start_time=T(start_h), end_time=T(end_h), attendance=10, status=status,
        )
    return _make
