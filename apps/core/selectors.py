"""
Reusable scoped querysets.

Selectors are the read-side counterpart to services: they never write, they
just return filtered querysets. Keeping the scope filter here means every
view, report and job filters rooms the same way — no duplicated logic.
"""
from apps.core.services import (
    SCOPE_DEPARTMENT,
    SCOPE_FACULTY,
    ResolvedScope,
)


def apply_room_scope(queryset, scope: ResolvedScope):
    """Filter a Room queryset (or any queryset with department/faculty FKs)
    down to the given resolved scope.

    Assumes the queryset's model exposes `department` and
    `department__faculty` relations (the Room model does).
    """
    if scope.key == SCOPE_DEPARTMENT and scope.department_id:
        return queryset.filter(department_id=scope.department_id)
    if scope.key == SCOPE_FACULTY and scope.faculty_id:
        return queryset.filter(department__faculty_id=scope.faculty_id)
    # University-wide: no filter.
    return queryset
