"""
Room inventory models.

Key design points carried from the prototype and the client discussions:

  * A room sits in BOTH hierarchies: a physical location (building/floor) and an
    owning organisational unit (department -> faculty). Both are explicit FKs.
  * Physical *type* is separated from *suitability*: a hall is one type but can
    be suitable for lectures, exams, events, meetings... (many-to-many tags).
    The booking checker matches a request's purpose to these tags.
  * Rooms are not created directly in the official inventory. They enter as a
    RoomDraft and only become a Room (with an official code) after verification
    -- see apps.rooms.services.RoomRegistrationService.
"""
from django.db import models

from apps.core.models import Building, Department, Floor, TimeStampedModel


class RoomStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    IN_USE = "in_use", "In use"
    BOOKED = "booked", "Booked"
    MAINTENANCE = "maintenance", "Under maintenance"
    CLEANING = "cleaning", "Cleaning in progress"
    CLOSED = "closed", "Closed"


UNAVAILABLE_STATUSES = {RoomStatus.MAINTENANCE, RoomStatus.CLEANING, RoomStatus.CLOSED}


class RoomType(TimeStampedModel):
    """Physical classification - lecture room, laboratory, hall, etc."""

    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=8, unique=True, help_text="Used in room codes, e.g. LT, LAB, HALL.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SuitabilityTag(TimeStampedModel):
    """What a room can be USED for - Lectures, Examinations, Events, etc."""

    name = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Equipment(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        verbose_name_plural = "equipment"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Room(TimeStampedModel):
    """An officially registered, bookable room."""

    # Official code issued at verification (e.g. UZ-LT-101). Unique & immutable.
    code = models.CharField(max_length=30, unique=True, editable=False)
    name = models.CharField(max_length=150)

    # Physical hierarchy
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="rooms")
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="rooms")

    # Organisational hierarchy (ownership -> drives scope & approval routing)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="rooms")

    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    suitability = models.ManyToManyField(SuitabilityTag, related_name="rooms", blank=True)
    equipment = models.ManyToManyField(Equipment, related_name="rooms", blank=True)

    capacity = models.PositiveIntegerField()
    condition = models.CharField(max_length=20, default="Good")
    accessibility = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.AVAILABLE)
    photo = models.ImageField(upload_to="rooms/", blank=True, null=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["status"]),
            models.Index(fields=["capacity"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def faculty(self):
        return self.department.faculty

    @property
    def faculty_id(self):
        return self.department.faculty_id

    @property
    def is_available(self) -> bool:
        return self.status == RoomStatus.AVAILABLE

    @property
    def is_unavailable(self) -> bool:
        return self.status in UNAVAILABLE_STATUSES

    def suits(self, tag_name: str) -> bool:
        """True if this room is tagged suitable for the given purpose tag."""
        return self.suitability.filter(name__iexact=tag_name).exists()


class DraftStatus(models.TextChoices):
    DRAFT = "draft", "Draft - pending verification"
    VERIFIED = "verified", "Verified - registered"
    REJECTED = "rejected", "Rejected"


class RoomDraft(TimeStampedModel):
    """
    A proposed room awaiting verification.

    Departments submit these; they are NOT bookable. Central administration /
    estates verifies them, at which point a Room with an official code is
    created (see RoomRegistrationService.verify).
    """

    name = models.CharField(max_length=150)
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="drafts")
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="drafts")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="drafts")
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="drafts")
    capacity = models.PositiveIntegerField()
    accessibility = models.CharField(max_length=60, blank=True)
    remarks = models.TextField(blank=True)
    # Same folder as Room.photo: the file is kept as-is when the draft is verified.
    photo = models.ImageField(upload_to="rooms/", blank=True, null=True)

    status = models.CharField(max_length=10, choices=DraftStatus.choices, default=DraftStatus.DRAFT)
    submitted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="submitted_drafts"
    )
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_drafts"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    resulting_room = models.OneToOneField(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="origin_draft"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name}"
