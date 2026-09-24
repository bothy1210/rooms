"""
Tests for the Draft -> Verify -> Official Code registration workflow.
This is the data-integrity guarantee the client specifically asked for.
"""
import pytest

from apps.accounts.models import User
from apps.accounts.permissions import ROLE_CENTRAL_ADMIN, ROLE_DEPT_ADMIN
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.rooms.models import DraftStatus, Room, RoomStatus, RoomType
from apps.rooms.services import RoomRegistrationError, RoomRegistrationService

pytestmark = pytest.mark.django_db


@pytest.fixture
def env():
    campus = Campus.objects.create(name="Main Campus", code="MC")
    building = Building.objects.create(campus=campus, name="Geography Building", code="GEO")
    floor = Floor.objects.create(building=building, name="1st", level=1)
    fac = Faculty.objects.create(name="Faculty of Science", code="SCI")
    dept = Department.objects.create(faculty=fac, name="Geoinformatics", code="GIS")
    lab = RoomType.objects.create(name="Laboratory", code="LAB")
    sec = User.objects.create_user("R100", full_name="Secretary", role=ROLE_DEPT_ADMIN, department=dept)
    admin = User.objects.create_user("R200", full_name="Central", role=ROLE_CENTRAL_ADMIN)
    return dict(building=building, floor=floor, dept=dept, lab=lab, sec=sec, admin=admin)


def test_submit_draft_is_not_bookable(env):
    draft = RoomRegistrationService.submit_draft(
        name="GIS Postgrad Lab", building=env["building"], floor=env["floor"],
        department=env["dept"], room_type=env["lab"], capacity=25, submitted_by=env["sec"],
    )
    assert draft.status == DraftStatus.DRAFT
    # No Room exists yet — a draft is not part of the bookable inventory.
    assert Room.objects.count() == 0


def test_verify_creates_room_with_official_code(env):
    draft = RoomRegistrationService.submit_draft(
        name="GIS Postgrad Lab", building=env["building"], floor=env["floor"],
        department=env["dept"], room_type=env["lab"], capacity=25, submitted_by=env["sec"],
    )
    room = RoomRegistrationService.verify(draft, verified_by=env["admin"])
    draft.refresh_from_db()

    assert room.code == "UZ-LAB-101"                 # first LAB code
    assert room.status == RoomStatus.AVAILABLE       # now bookable
    assert draft.status == DraftStatus.VERIFIED
    assert draft.resulting_room_id == room.id
    assert Room.objects.count() == 1


def test_codes_increment_and_never_collide(env):
    for i in range(3):
        d = RoomRegistrationService.submit_draft(
            name=f"Lab {i}", building=env["building"], floor=env["floor"],
            department=env["dept"], room_type=env["lab"], capacity=20, submitted_by=env["sec"],
        )
        RoomRegistrationService.verify(d, verified_by=env["admin"])
    codes = sorted(Room.objects.values_list("code", flat=True))
    assert codes == ["UZ-LAB-101", "UZ-LAB-102", "UZ-LAB-103"]


def test_cannot_verify_twice(env):
    draft = RoomRegistrationService.submit_draft(
        name="Once", building=env["building"], floor=env["floor"],
        department=env["dept"], room_type=env["lab"], capacity=10, submitted_by=env["sec"],
    )
    RoomRegistrationService.verify(draft, verified_by=env["admin"])
    with pytest.raises(RoomRegistrationError):
        RoomRegistrationService.verify(draft, verified_by=env["admin"])


def test_reject_draft(env):
    draft = RoomRegistrationService.submit_draft(
        name="Bad", building=env["building"], floor=env["floor"],
        department=env["dept"], room_type=env["lab"], capacity=10, submitted_by=env["sec"],
    )
    RoomRegistrationService.reject(draft, verified_by=env["admin"])
    draft.refresh_from_db()
    assert draft.status == DraftStatus.REJECTED
    assert Room.objects.count() == 0
