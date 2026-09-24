"""
Booking models.

A booking targets one room for a date + time window, for a stated purpose. The
service layer checks conflicts, capacity and suitability before a booking is
created; approval routing (to the OWNING unit) lives in the approvals app.
"""
from django.db import models

from apps.rooms.models import Room


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class Purpose(models.TextChoices):
    LECTURE = "lecture", "Lecture"
    EXAMINATION = "examination", "Examination"
    MEETING = "meeting", "Meeting"
    WORKSHOP = "workshop", "Workshop"
    CONFERENCE = "conference", "Conference"
    EVENT = "event", "University event"


# Maps a booking purpose to the SuitabilityTag name a room must carry.
PURPOSE_TO_TAG = {
    Purpose.LECTURE: "Lectures",
    Purpose.EXAMINATION: "Examinations",
    Purpose.MEETING: "Meetings",
    Purpose.WORKSHOP: "Workshops",
    Purpose.CONFERENCE: "Conferences",
    Purpose.EVENT: "Events",
}


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    requester = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="bookings"
    )
    requester_name = models.CharField(max_length=150)
    requester_dept = models.CharField(max_length=150, blank=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    attendance = models.PositiveIntegerField(default=0)
    equipment_note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    approved_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "start_time"]
        indexes = [
            models.Index(fields=["room", "date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["date", "start_time"]),   # calendar month / bookings list
            models.Index(fields=["status", "date"]),       # pending queue, oldest first
        ]

    def __str__(self):
        return f"{self.room.code} · {self.date} {self.start_time}-{self.end_time} ({self.get_status_display()})"

    @property
    def is_cross_unit(self) -> bool:
        """True if the requester's department differs from the room's owner."""
        if not self.requester or not self.requester.department_id:
            return False
        return self.requester.department_id != self.room.department_id
