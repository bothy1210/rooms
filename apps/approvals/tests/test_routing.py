"""
Tests for approval routing & scoped decisions.

The crucial guarantee: a cross-unit booking routes to the ROOM's owning office,
and only an in-scope approver may act on it.
"""
import datetime as dt

import pytest

from apps.accounts.models import User
from apps.accounts.permissions import ROLE_CENTRAL_ADMIN, ROLE_DEPT_ADMIN
from apps.approvals.services import ApprovalError, ApprovalService
from apps.bookings.models import Booking, BookingStatus, Purpose
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.rooms.models import Room, RoomStatus, RoomType

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    campus = Campus.objects.create(name="Main", code="MC")
    b = Building.objects.create(campus=campus, name="Admin Block", code="ADM")
    f = Floor.objects.create(building=b, name="Ground", level=0)
    sci = Faculty.objects.create(name="Faculty of Science", code="SCI")
    admin_fac = Faculty.objects.create(name="Central Administration", code="ADM", is_administrative=True)
    geo = Department.objects.create(faculty=sci, name="Geoinformatics", code="GIS")
    central = Department.objects.create(faculty=admin_fac, name="Central Administration", code="CADM")
    mr = RoomType.objects.create(name="Meeting room", code="MR")

    # A room OWNED by Central Administration (e.g. the Council Chamber).
    council = Room.objects.create(code="UZ-MR-101", name="Council Chamber", building=b, floor=f,
                                  department=central, room_type=mr, capacity=40, status=RoomStatus.AVAILABLE)

    geo_secretary = User.objects.create_user("R10", full_name="Geo Sec", role=ROLE_DEPT_ADMIN, department=geo)
    central_admin = User.objects.create_user("R20", full_name="Registrar", role=ROLE_DEPT_ADMIN, department=central)
    planner = User.objects.create_user("R30", full_name="Planner", role=ROLE_CENTRAL_ADMIN)

    # A Geoinformatics user books the Council Chamber (cross-unit request).
    booking = Booking.objects.create(
        room=council, requester=geo_secretary, requester_name="Geo Sec", requester_dept="Geoinformatics",
        purpose=Purpose.MEETING, date=dt.date.today(), start_time=dt.time(10), end_time=dt.time(12),
        attendance=20, status=BookingStatus.PENDING,
    )
    return dict(booking=booking, council=council, central=central,
                geo_secretary=geo_secretary, central_admin=central_admin, planner=planner)


def test_route_goes_to_room_owner_not_requester(setup):
    routed = ApprovalService.route(setup["booking"])
    assert routed == setup["central"]              # room owner, not Geoinformatics


def test_requester_cannot_approve_cross_unit_request(setup):
    # The Geoinformatics secretary submitted it but the room is Central's —
    # they must NOT be able to approve it.
    with pytest.raises(ApprovalError):
        ApprovalService.decide(setup["booking"], user=setup["geo_secretary"], approve=True)


def test_owning_office_can_approve(setup):
    booking = ApprovalService.decide(setup["booking"], user=setup["central_admin"], approve=True)
    assert booking.status == BookingStatus.APPROVED
    assert booking.approved_by == "Registrar"


def test_central_admin_can_approve_anything(setup):
    booking = ApprovalService.decide(setup["booking"], user=setup["planner"], approve=True)
    assert booking.status == BookingStatus.APPROVED


def test_pending_for_scopes_to_owned_rooms(setup):
    # Central admin's secretary sees the request (their room); Geo secretary does not.
    assert setup["booking"] in ApprovalService.pending_for(setup["central_admin"])
    assert setup["booking"] not in ApprovalService.pending_for(setup["geo_secretary"])
    assert setup["booking"] in ApprovalService.pending_for(setup["planner"])  # sees all


def test_cannot_decide_twice(setup):
    ApprovalService.decide(setup["booking"], user=setup["central_admin"], approve=True)
    with pytest.raises(ApprovalError):
        ApprovalService.decide(setup["booking"], user=setup["central_admin"], approve=False)


def test_approval_reflects_on_room_status(setup):
    assert setup["council"].status == RoomStatus.AVAILABLE
    ApprovalService.decide(setup["booking"], user=setup["central_admin"], approve=True)
    setup["council"].refresh_from_db()
    assert setup["council"].status == RoomStatus.BOOKED
