"""
Approval workflow models.

A booking request is routed to the office responsible for the OWNING unit of the
room (concept note 7.4). Cross-unit requests therefore go to the room owner, not
the requester's own department. Each decision is recorded as an ApprovalStep for
accountability.
"""
from django.db import models

from apps.bookings.models import Booking


class ApprovalDecision(models.TextChoices):
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    RETURNED = "returned", "Returned for correction"


class ApprovalStep(models.Model):
    """One decision on a booking by a responsible office."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="approval_steps")
    # The organisational unit the request was routed to (room's owning department).
    routed_to_department = models.ForeignKey(
        "core.Department", on_delete=models.PROTECT, related_name="approval_steps"
    )
    decision = models.CharField(max_length=10, choices=ApprovalDecision.choices)
    decided_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="approval_decisions"
    )
    comment = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]

    def __str__(self):
        return f"BK-{self.booking_id} {self.get_decision_display()} by {self.decided_by}"
