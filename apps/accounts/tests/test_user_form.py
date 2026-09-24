"""Adding an account: a username to sign in with, and a department and
faculty that are typed rather than picked from a list."""
import pytest
from django.contrib.auth import authenticate

from apps.accounts.forms import UserCreateForm
from apps.accounts.models import User
from apps.accounts.permissions import ROLE_DEPT_ADMIN, ROLE_VIEWER
from apps.core.models import Department, Faculty

pytestmark = pytest.mark.django_db

PASSWORD = "Kopje-Harare-2026"


def _form(**fields):
    data = {"username": "tmoyo", "full_name": "Tendai Moyo", "email": "", "role": ROLE_VIEWER,
            "department_name": "", "faculty_name": "", "is_active": "on",
            "password1": PASSWORD, "password2": PASSWORD}
    data.update(fields)
    return UserCreateForm(data)


@pytest.fixture
def science():
    fac = Faculty.objects.create(name="Faculty of Science", code="SCI")
    return fac, Department.objects.create(faculty=fac, name="Geoinformatics", code="GEO")


def test_the_new_user_signs_in_with_their_username_in_any_case():
    form = _form()
    assert form.is_valid(), form.errors
    user = form.save()
    assert authenticate(username="TMOYO", password=PASSWORD) == user


def test_a_username_that_differs_only_in_case_is_refused():
    User.objects.create_user("TMoyo", password="x")
    form = _form(username="tmoyo")
    assert not form.is_valid() and "username" in form.errors


def test_a_typed_department_is_matched_and_brings_its_faculty(science):
    fac, geo = science
    form = _form(role=ROLE_DEPT_ADMIN, department_name="  geoinformatics ")
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.department == geo and user.faculty == fac
    assert Department.objects.count() == 1                    # nothing new was added


def test_a_department_not_yet_in_the_system_is_added_under_the_typed_faculty(science):
    fac, _ = science
    form = _form(role=ROLE_DEPT_ADMIN, department_name="Physics", faculty_name="faculty of science")
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.department.name == "Physics" and user.department.faculty == fac
    assert user.department.code and user.faculty == fac


def test_a_new_department_needs_its_faculty():
    form = _form(role=ROLE_DEPT_ADMIN, department_name="Physics")
    assert not form.is_valid() and "faculty_name" in form.errors
    assert not Department.objects.exists()


def test_a_new_faculty_is_added_with_a_code_of_its_own(science):
    form = _form(role=ROLE_DEPT_ADMIN, department_name="Soil Science",
                 faculty_name="Faculty of Agriculture")
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.faculty.name == "Faculty of Agriculture" and user.faculty.code == "AGRI"
    assert user.department.faculty == user.faculty and user.department.code == "SS"


def test_a_departmental_administrator_still_needs_a_scope():
    form = _form(role=ROLE_DEPT_ADMIN)
    assert not form.is_valid() and "department_name" in form.errors
