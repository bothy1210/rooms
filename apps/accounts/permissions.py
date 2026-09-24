"""
Role → capability matrix.

The concept note defines two broad user categories (Admin User, Read-Only
Viewer), with the admin category carrying internal permission levels. We model
that as four concrete roles and a capability matrix, so every view can ask a
single question: `has_capability(user, "verify_room")`.

Scope (which rooms an admin may touch) is enforced separately by
apps.core.services.ScopeService — a role says *what* you may do, scope says
*where*.
"""

# ── Roles ──────────────────────────────────────────────────────────────
ROLE_CENTRAL_ADMIN = "central_admin"   # planning / estates / system admin — all rooms
ROLE_DEPT_ADMIN = "dept_admin"         # department secretary / faculty administrator — scoped
ROLE_APPROVER = "approver"             # office that only approves (e.g. exams office)
ROLE_VIEWER = "viewer"                 # read-only: lecturers, HODs, student reps

ROLE_CHOICES = [
    (ROLE_CENTRAL_ADMIN, "Central Administrator"),
    (ROLE_DEPT_ADMIN, "Departmental Administrator"),
    (ROLE_APPROVER, "Approver"),
    (ROLE_VIEWER, "Read-Only Viewer"),
]

# ── Capabilities ───────────────────────────────────────────────────────
CAP_VIEW_DASHBOARD = "view_dashboard"
CAP_SUBMIT_BOOKING = "submit_booking"
CAP_EDIT_ROOM = "edit_room"            # subject to scope
CAP_UPDATE_STATUS = "update_status"    # subject to scope
CAP_REGISTER_ROOM = "register_room"    # submit a Draft
CAP_VERIFY_ROOM = "verify_room"        # verify a Draft & issue official code (central only)
CAP_APPROVE_BOOKING = "approve_booking"  # subject to scope
CAP_MANAGE_USERS = "manage_users"
CAP_VIEW_REPORTS = "view_reports"
CAP_EXPORT_REPORTS = "export_reports"
CAP_VIEW_ALL_ROOMS = "view_all_rooms"  # may switch to the university-wide scope (viewing only)

# ── Matrix ─────────────────────────────────────────────────────────────
# What each role is *allowed* to do (before scope is applied).
CAPABILITY_MATRIX = {
    ROLE_CENTRAL_ADMIN: {
        CAP_VIEW_DASHBOARD, CAP_SUBMIT_BOOKING, CAP_EDIT_ROOM, CAP_UPDATE_STATUS,
        CAP_REGISTER_ROOM, CAP_VERIFY_ROOM, CAP_APPROVE_BOOKING, CAP_MANAGE_USERS,
        CAP_VIEW_REPORTS, CAP_EXPORT_REPORTS, CAP_VIEW_ALL_ROOMS,
    },
    ROLE_DEPT_ADMIN: {
        CAP_VIEW_DASHBOARD, CAP_SUBMIT_BOOKING, CAP_EDIT_ROOM, CAP_UPDATE_STATUS,
        CAP_REGISTER_ROOM, CAP_APPROVE_BOOKING, CAP_VIEW_REPORTS, CAP_EXPORT_REPORTS,
    },
    ROLE_APPROVER: {
        # Sees every room university-wide (they need to judge and suggest venues),
        # but may still only approve requests routed to their own office.
        CAP_VIEW_DASHBOARD, CAP_SUBMIT_BOOKING, CAP_APPROVE_BOOKING, CAP_VIEW_REPORTS,
        CAP_VIEW_ALL_ROOMS,
    },
    ROLE_VIEWER: {
        CAP_VIEW_DASHBOARD, CAP_SUBMIT_BOOKING, CAP_VIEW_REPORTS,
    },
}


def capabilities_for(role: str) -> set[str]:
    return CAPABILITY_MATRIX.get(role, set())


def has_capability(user, capability: str) -> bool:
    """True if the user's role grants the capability (ignores scope)."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return capability in capabilities_for(getattr(user, "role", ROLE_VIEWER))
