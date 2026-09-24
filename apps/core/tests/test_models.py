"""Tests for the core hierarchy models."""
import pytest

from apps.core.models import Building, Campus, Department, Faculty, Floor

pytestmark = pytest.mark.django_db


def test_physical_hierarchy_str():
    campus = Campus.objects.create(name="Main Campus", code="MC")
    building = Building.objects.create(campus=campus, name="Science Block", code="SCI")
    floor = Floor.objects.create(building=building, name="Ground", level=0)

    assert str(campus) == "Main Campus"
    assert "Science Block" in str(building)
    assert "Ground" in str(floor)


def test_organisational_hierarchy_str():
    faculty = Faculty.objects.create(name="Faculty of Science", code="SCI")
    dept = Department.objects.create(faculty=faculty, name="Geoinformatics", code="GEO")

    assert str(faculty) == "Faculty of Science"
    assert "Geoinformatics" in str(dept)
    assert dept.faculty == faculty


def test_building_code_unique_per_campus():
    c1 = Campus.objects.create(name="Main Campus", code="MC")
    Building.objects.create(campus=c1, name="Science Block", code="SCI")
    # Same code on the same campus should violate the unique constraint.
    with pytest.raises(Exception):
        Building.objects.create(campus=c1, name="Science Annex", code="SCI")


def test_administrative_faculty_flag():
    admin_fac = Faculty.objects.create(name="Central Administration", code="ADM", is_administrative=True)
    assert admin_fac.is_administrative is True
