"""
Approval service — routing and decisions.

`route()` answers "which office should action this request?" — always the
owning department of the *room* (so a cross-unit booking goes to the room's
owner, never the requester's own unit). `decide()` records the approve/reject
decision, enforces that only an in-scope approver may act, updates the booking,
and (on approval) reflects the booking on the room's live status.
"""
from django.db import transaction

from apps.approvals.models import ApprovalDecision, ApprovalStep
from apps.audit.services import log_change
from apps.bookings.models import Booking, BookingStatus
from apps.notifications.services import notify
from apps.rooms.models import RoomStatus


class ApprovalError(Exception):
    """Raised when a decision is not permitted or the booking is not pending."""


class ApprovalService:
    @staticmethod
    def route(booking: Booking):
        """Return the department the request is routed to — the room's owner."""
        return booking.room.department

    @staticmethod
    def pending_for(user):
        """Bookings this user may action, honouring role + scope.

        Central admins see all pending requests; scoped approvers see only those
        whose room belongs to their department/faculty.
        """
        qs = Booking.objects.filter(status=BookingStatus.PENDING).select_related(
            "room", "room__department", "room__department__faculty"
        )
        if getattr(user, "is_central_admin", False):
            return qs
        if getattr(user, "department_id", None):
            return qs.filter(room__department_id=user.department_id)
        if getattr(user, "faculty_id", None):
            return qs.filter(room__department__faculty_id=user.faculty_id)
        return qs.none()

    @classmethod
    @transaction.atomic
    def decide(cls, booking: Booking, *, user, approve: bool, comment="") -> Booking:
        if booking.status != BookingStatus.PENDING:
            raise ApprovalError(f"Booking BK-{booking.pk} is already {booking.get_status_display()}.")
        # Role + scope: may this user approve for the room's owning unit?
        if not user.can_approve_for(booking.room):
            raise ApprovalError("This request is outside your approval scope.")

        routed_to = cls.route(booking)
        decision = ApprovalDecision.APPROVED if approve else ApprovalDecision.REJECTED
        booking.status = BookingStatus.APPROVED if approve else BookingStatus.REJECTED
        if approve:
            booking.approved_by = user.full_name or user.username
            # Reflect an approved same-time booking on the room's live status.
            if booking.room.status == RoomStatus.AVAILABLE:
                booking.room.status = RoomStatus.BOOKED
                booking.room.save(update_fields=["status", "updated_at"])
        booking.save(update_fields=["status", "approved_by"])

        ApprovalStep.objects.create(
            booking=booking, routed_to_department=routed_to,
            decision=decision, decided_by=user, comment=comment,
        )
        log_change(
            "Booking approved" if approve else "Booking rejected",
            f"BK-{booking.pk} — {booking.room.code}",
            "Pending approval", booking.get_status_display(),
            user=user,
        )
        notify(
            user=booking.requester,
            message=(
                f"Your booking BK-{booking.pk} for {booking.room.name} was "
                f"{'approved' if approve else 'rejected'}."
            ),
        )
        return booking
