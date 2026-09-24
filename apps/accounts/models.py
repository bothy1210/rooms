"""
Custom user model.

Identified by a username, carries a single role plus an organisational scope
(department and/or faculty). The scope fields are what apps.core.ScopeService
reads to decide which rooms a user sees on the dashboard, and the capability
helpers wrap the role -> capability matrix so views can ask `user.can(...)`.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.accounts.managers import UserManager
from apps.accounts.permissions import (
    ROLE_APPROVER,
    ROLE_CENTRAL_ADMIN,
    ROLE_CHOICES,
    ROLE_DEPT_ADMIN,
    ROLE_VIEWER,
    CAP_APPROVE_BOOKING,
    CAP_EDIT_ROOM,
    CAP_UPDATE_STATUS,
    has_capability,
)
from apps.core.models import Department, Faculty


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        "Username", max_length=150, unique=True,
        help_text="The name this person signs in with, e.g. tmoyo. Matched without regard to case.",
    )
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)

    # Organisational scope - an admin is scoped to these.
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="members"
    )
    faculty = models.ForeignKey(
        Faculty, null=True, blank=True, on_delete=models.SET_NULL, related_name="members"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.full_name or self.username} ({self.username})"

    def save(self, *args, **kwargs):
        # Keep faculty consistent with department when a department is set.
        if self.department and not self.faculty_id:
            self.faculty = self.department.faculty
        super().save(*args, **kwargs)

    # -- Role helpers (read by ScopeService & mixins) --
    @property
    def is_central_admin(self) -> bool:
        return self.role == ROLE_CENTRAL_ADMIN or self.is_superuser

    @property
    def is_admin_user(self) -> bool:
        """Any role that can manage data (not a read-only viewer)."""
        return self.role in {ROLE_CENTRAL_ADMIN, ROLE_DEPT_ADMIN, ROLE_APPROVER}

    # -- Capability helpers --
    def can(self, capability: str) -> bool:
        """Role-level check (ignores scope)."""
        return has_capability(self, capability)

    def can_edit_room(self, room) -> bool:
        """Role AND scope: may this user edit this specific room?"""
        if not self.can(CAP_EDIT_ROOM):
            return False
        return self._in_scope(room)

    def can_update_status(self, room) -> bool:
        if not self.can(CAP_UPDATE_STATUS):
            return False
        return self._in_scope(room)

    def can_approve_for(self, room) -> bool:
        """May this user approve a booking for this room's owning unit?"""
        if not self.can(CAP_APPROVE_BOOKING):
            return False
        return self._in_scope(room)

    def _in_scope(self, room) -> bool:
        """Central admins: everything. Department-scoped admins: their own
        department only. Faculty-scoped admins (a faculty but no department):
        any room in their faculty."""
        if self.is_central_admin:
            return True
        if self.department_id:
            # Scoped to a specific department — must match exactly.
            return room.department_id == self.department_id
        if self.faculty_id:
            # Faculty-level admin — any room whose department is in that faculty.
            return bool(room.department and room.department.faculty_id == self.faculty_id)
        return False
