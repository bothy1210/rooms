"""Tests for scoped dashboard aggregation and the Excel export."""
from types import SimpleNamespace

import pytest

from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.core.services import ScopeService
from apps.dashboards import selectors
from apps.dashboards.exports.excel import build_utilisation_xlsx
from apps.rooms.models import Room, RoomStatus, RoomType

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    campus = Campus.objects.create(name="Main", code="MC")
    b1 = Building.objects.create(campus=campus, name="Science", code="SCI")
    b2 = Building.objects.create(campus=campus, name="Law", code="LAW")
    f1 = Floor.objects.create(building=b1, name="Ground", level=0)
    f2 = Floor.objects.create(building=b2, name="Ground", level=0)
    sci = Faculty.objects.create(name="Faculty of Science", code="SCI")
    law_fac = Faculty.objects.create(name="Faculty of Law", code="LAW")
    geo = Department.objects.create(faculty=sci, name="Geoinformatics", code="GIS")
    law = Department.objects.create(faculty=law_fac, name="Law", code="LAW")
    lt = RoomType.objects.create(name="Lecture room", code="LT")

    def mk(code, dept, bld, flr, cap, status):
        return Room.objects.create(code=code, name=code, building=bld, floor=flr,
                                   department=dept, room_type=lt, capacity=cap, status=status)
    mk("UZ-LT-101", geo, b1, f1, 40, RoomStatus.AVAILABLE)
    mk("UZ-LT-102", geo, b1, f1, 100, RoomStatus.IN_USE)
    mk("UZ-LT-103", geo, b1, f1, 60, RoomStatus.BOOKED)
    mk("UZ-LT-104", law, b2, f2, 200, RoomStatus.MAINTENANCE)
    return dict(geo=geo, sci=sci)


def _user(**kw):
    d = dict(department_id=None, faculty_id=None, is_central_admin=False, department=None, faculty=None)
    d.update(kw)
    return SimpleNamespace(**d)


def test_status_counts_university_wide(data):
    scope = ScopeService.resolve(_user(is_central_admin=True), "uni")
    s = selectors.status_counts(scope)
    assert s["total"] == 4
    assert s["available"] == 1
    assert s["in_use"] == 1
    assert s["booked"] == 1
    assert s["unavailable"] == 1
    assert s["capacity"] == 400
    # utilisation = (in_use + booked)/total = 2/4 = 50%
    assert s["utilisation"] == 50


def test_status_counts_are_scoped(data):
    user = _user(department_id=data["geo"].id, faculty_id=data["sci"].id)
    scope = ScopeService.resolve(user, "dept")
    s = selectors.status_counts(scope)
    assert s["total"] == 3                       # only Geoinformatics rooms
    assert s["unavailable"] == 0                 # the maintenance room is Law's


def test_utilisation_by_building(data):
    scope = ScopeService.resolve(_user(is_central_admin=True), "uni")
    rows = selectors.utilisation_by_building(scope)
    by_label = {r["label"]: r for r in rows}
    assert by_label["Science"]["rooms"] == 3
    assert by_label["Science"]["utilisation"] == 67   # 2 of 3 used, rounded


def test_excel_export_returns_xlsx(data):
    scope = ScopeService.resolve(_user(is_central_admin=True), "uni")
    rows = selectors.utilisation_by_building(scope)
    response = build_utilisation_xlsx(rows)
    assert response["Content-Type"].startswith("application/vnd.openxmlformats")
    assert response.content[:2] == b"PK"          # xlsx is a zip → starts with PK
