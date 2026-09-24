"""
Tests for ScopeService — the logic that keeps dashboards relevant per user.

These use lightweight stand-in user objects (SimpleNamespace) so the scope
logic can be tested without the accounts app being built yet.
"""
from types import SimpleNamespace

from apps.core.services import (
    SCOPE_DEPARTMENT,
    SCOPE_FACULTY,
    SCOPE_UNIVERSITY,
    ScopeService,
)


def make_user(**kwargs):
    defaults = dict(
        is_central_admin=False,
        department_id=None,
        faculty_id=None,
        department=None,
        faculty=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_department_user_defaults_to_department_scope():
    user = make_user(department_id=5, faculty_id=2, department="Geoinformatics")
    assert ScopeService.default_scope(user) == SCOPE_DEPARTMENT
    assert set(ScopeService.available_scopes(user)) == {SCOPE_DEPARTMENT, SCOPE_FACULTY}


def test_central_admin_defaults_to_university_scope():
    user = make_user(is_central_admin=True)
    assert ScopeService.default_scope(user) == SCOPE_UNIVERSITY
    assert SCOPE_UNIVERSITY in ScopeService.available_scopes(user)


def test_department_user_cannot_force_university_scope():
    """Security: a scoped user requesting ?scope=uni is capped at their allowed set."""
    user = make_user(department_id=5, faculty_id=2, department="Geoinformatics")
    resolved = ScopeService.resolve(user, SCOPE_UNIVERSITY)
    # Falls back to their default (department) instead of honouring uni-wide.
    assert resolved.key == SCOPE_DEPARTMENT
    assert resolved.department_id == 5


def test_resolve_faculty_scope_sets_only_faculty_filter():
    user = make_user(department_id=5, faculty_id=2, faculty="Faculty of Science")
    resolved = ScopeService.resolve(user, SCOPE_FACULTY)
    assert resolved.key == SCOPE_FACULTY
    assert resolved.faculty_id == 2
    assert resolved.department_id is None


def test_central_admin_can_resolve_university_scope():
    user = make_user(is_central_admin=True)
    resolved = ScopeService.resolve(user, SCOPE_UNIVERSITY)
    assert resolved.key == SCOPE_UNIVERSITY
    assert resolved.department_id is None
    assert resolved.faculty_id is None
