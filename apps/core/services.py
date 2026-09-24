"""
Scope service — resolves the three dashboard scopes discussed with the client:

    "dept"  → My Department   (the user's own department)
    "fac"   → My Faculty      (the user's whole faculty)
    "uni"   → University-wide  (all rooms)

This is what makes the dashboard relevant to each user instead of dumping all
university rooms on everyone. Views ask ScopeService which scopes a user may
select and which one to default to; selectors then filter querysets by it.
"""
from dataclasses import dataclass

from apps.accounts.permissions import CAP_VIEW_ALL_ROOMS, has_capability

# Scope identifiers used throughout the app.
SCOPE_DEPARTMENT = "dept"
SCOPE_FACULTY = "fac"
SCOPE_UNIVERSITY = "uni"

SCOPE_LABELS = {
    SCOPE_DEPARTMENT: "My Department",
    SCOPE_FACULTY: "My Faculty",
    SCOPE_UNIVERSITY: "University-wide",
}


@dataclass(frozen=True)
class ResolvedScope:
    """The concrete scope applied to a request."""

    key: str                      # "dept" | "fac" | "uni"
    label: str                    # human-readable label for the chip
    department_id: int | None     # set when key == "dept"
    faculty_id: int | None        # set when key == "dept" or "fac"


class ScopeService:
    """Pure logic — no DB writes. Safe to call from views, jobs and the API."""

    @staticmethod
    def available_scopes(user) -> list[str]:
        """Which scope buttons a user may see.

        Central administrators and planning officers may view the whole
        university; ordinary department/faculty users are capped at their
        own faculty.
        """
        if getattr(user, "is_central_admin", False):
            return [SCOPE_DEPARTMENT, SCOPE_FACULTY, SCOPE_UNIVERSITY]
        # A user with a department gets dept + faculty; faculty-only users get faculty.
        if getattr(user, "department_id", None):
            scopes = [SCOPE_DEPARTMENT, SCOPE_FACULTY]
        elif getattr(user, "faculty_id", None):
            scopes = [SCOPE_FACULTY]
        else:
            return [SCOPE_UNIVERSITY]
        # Approvers judge requests against the whole estate, so they may look wider.
        if has_capability(user, CAP_VIEW_ALL_ROOMS):
            scopes.append(SCOPE_UNIVERSITY)
        return scopes

    @staticmethod
    def default_scope(user) -> str:
        """The scope a user lands on when they open the dashboard."""
        if getattr(user, "is_central_admin", False) or has_capability(user, CAP_VIEW_ALL_ROOMS):
            return SCOPE_UNIVERSITY
        if getattr(user, "department_id", None):
            return SCOPE_DEPARTMENT
        if getattr(user, "faculty_id", None):
            return SCOPE_FACULTY
        return SCOPE_UNIVERSITY

    @classmethod
    def resolve(cls, user, requested: str | None) -> ResolvedScope:
        """Turn a requested scope (e.g. from ?scope=fac) into a concrete filter.

        Falls back to the user's default if the request is missing or not
        permitted for them (prevents a department user forcing a uni-wide view
        via the URL).
        """
        allowed = cls.available_scopes(user)
        key = requested if requested in allowed else cls.default_scope(user)

        faculty_id = getattr(user, "faculty_id", None)
        department_id = getattr(user, "department_id", None)

        if key == SCOPE_DEPARTMENT:
            label = f"{SCOPE_LABELS[key]} · {getattr(user, 'department', None) or ''}".strip(" ·")
            return ResolvedScope(key, label, department_id, faculty_id)
        if key == SCOPE_FACULTY:
            label = f"{SCOPE_LABELS[key]} · {getattr(user, 'faculty', None) or ''}".strip(" ·")
            return ResolvedScope(key, label, None, faculty_id)
        return ResolvedScope(SCOPE_UNIVERSITY, SCOPE_LABELS[SCOPE_UNIVERSITY], None, None)
