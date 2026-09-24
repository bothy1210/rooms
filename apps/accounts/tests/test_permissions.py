"""
Tests for the role -> capability matrix and scoped edit/approve checks.
These are the guarantees the whole RBAC design rests on.
"""
import pytest

from apps.accounts.models import User
from apps.accounts.permissions import (
    CAP_VERIFY_ROOM,
    CAP_EDIT_ROOM,
    CAP_MANAGE_USERS,
    ROLE_CENTRAL_ADMIN,
    ROLE_DEPT_ADMIN,
    ROLE_VIEWER,
)
from apps.core.models import Department, Faculty

pytestmark = pytest.mark.django_db


@pytest.fixture
def science():
    fac = Faculty.objects.create(name="Faculty of Science", code="SCI")
    geo = Department.objects.create(faculty=fac, name="Geoinformatics", code="GEO")
    phys = Department.objects.create(faculty=fac, name="Physics", code="PHY")
    return fac, geo, phys


class _Room:
    """Lightweight room stand-in (rooms app not required for these checks)."""
    def __init__(self, department):
        self.department = department
        self.department_id = department.id


def test_viewer_has_minimal_capabilities(science):
    _, geo, _ = science
    u = User.objects.create_user("R1", full_name="Viewer", role=ROLE_VIEWER, department=geo)
    assert not u.can(CAP_EDIT_ROOM)
    assert not u.can(CAP_VERIFY_ROOM)
    assert not u.can(CAP_MANAGE_USERS)


def test_dept_admin_can_edit_only_own_department(science):
    _, geo, phys = science
    u = User.objects.create_user("R2", full_name="Geo Sec", role=ROLE_DEPT_ADMIN, department=geo)
    assert u.can(CAP_EDIT_ROOM)                     # role allows editing
    assert u.can_edit_room(_Room(geo))              # own department -> yes
    assert not u.can_edit_room(_Room(phys))         # other department -> no


def test_dept_admin_cannot_verify_rooms(science):
    _, geo, _ = science
    u = User.objects.create_user("R3", full_name="Geo Sec", role=ROLE_DEPT_ADMIN, department=geo)
    assert not u.can(CAP_VERIFY_ROOM)               # verification is central-only


def test_central_admin_can_edit_any_department(science):
    _, geo, phys = science
    u = User.objects.create_user("R4", full_name="Planner", role=ROLE_CENTRAL_ADMIN)
    assert u.can_edit_room(_Room(geo))
    assert u.can_edit_room(_Room(phys))
    assert u.can(CAP_VERIFY_ROOM)
    assert u.can(CAP_MANAGE_USERS)


def test_department_sets_faculty_automatically(science):
    fac, geo, _ = science
    u = User.objects.create_user("R5", full_name="Auto Fac", role=ROLE_DEPT_ADMIN, department=geo)
    assert u.faculty_id == fac.id                   # save() backfills faculty


def test_username_is_kept_as_typed_and_found_regardless_of_case():
    u = User.objects.create_user(" TMoyo ", full_name="Case", password="x")
    assert u.username == "TMoyo"
    assert User.objects.get_by_natural_key("tmoyo") == u
