"""Tests for scoped room search/filtering."""
import pytest

from types import SimpleNamespace
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.core.services import ScopeService
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.rooms.selectors import search_rooms

pytestmark = pytest.mark.django_db


@pytest.fixture
def rooms_env():
    campus = Campus.objects.create(name="Main", code="MC")
    b = Building.objects.create(campus=campus, name="Science", code="SCI")
    f = Floor.objects.create(building=b, name="Ground", level=0)
    sci = Faculty.objects.create(name="Faculty of Science", code="SCI")
    geo = Department.objects.create(faculty=sci, name="Geoinformatics", code="GIS")
    phys = Department.objects.create(faculty=sci, name="Physics", code="PHY")
    law_fac = Faculty.objects.create(name="Faculty of Law", code="LAW")
    law = Department.objects.create(faculty=law_fac, name="Law", code="LAW")
    lt = RoomType.objects.create(name="Lecture room", code="LT")

    def mk(code, dept, cap, status=RoomStatus.AVAILABLE):
        return Room.objects.create(code=code, name=code, building=b, floor=f,
                                   department=dept, room_type=lt, capacity=cap, status=status)
    mk("UZ-LT-101", geo, 40)
    mk("UZ-LT-102", geo, 120)
    mk("UZ-LT-103", phys, 300)
    mk("UZ-LT-104", law, 80, RoomStatus.MAINTENANCE)
    return dict(geo=geo, sci=sci)


def _user(department_id=None, faculty_id=None, is_central_admin=False):
    return SimpleNamespace(department_id=department_id, faculty_id=faculty_id,
                           is_central_admin=is_central_admin, department=None, faculty=None,
                           is_authenticated=True)


def test_department_scope_limits_to_own_rooms(rooms_env):
    user = _user(department_id=rooms_env["geo"].id, faculty_id=rooms_env["sci"].id)
    scope = ScopeService.resolve(user, "dept")
    assert search_rooms(scope=scope).count() == 2      # only Geoinformatics rooms


def test_faculty_scope_includes_sibling_departments(rooms_env):
    user = _user(department_id=rooms_env["geo"].id, faculty_id=rooms_env["sci"].id)
    scope = ScopeService.resolve(user, "fac")
    # Geoinformatics (2) + Physics (1) in Faculty of Science; Law excluded.
    assert search_rooms(scope=scope).count() == 3


def test_university_scope_sees_all(rooms_env):
    user = _user(is_central_admin=True)
    scope = ScopeService.resolve(user, "uni")
    assert search_rooms(scope=scope).count() == 4


def test_min_capacity_filter(rooms_env):
    user = _user(is_central_admin=True)
    scope = ScopeService.resolve(user, "uni")
    assert search_rooms(scope=scope, min_capacity=100).count() == 2   # 120 and 300


def test_unavailable_status_filter(rooms_env):
    user = _user(is_central_admin=True)
    scope = ScopeService.resolve(user, "uni")
    assert search_rooms(scope=scope, status="unavailable").count() == 1  # the maintenance room
