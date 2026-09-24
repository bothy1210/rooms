"""Usage log - a historical record of room status changes over time (concept note 8.4)."""
from django.db import models

from apps.rooms.models import Room, RoomStatus


class UsageLog(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="usage_logs")
    status = models.CharField(max_length=20, choices=RoomStatus.choices)
    changed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="usage_changes"
    )
    note = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["room", "-timestamp"])]

    def __str__(self):
        return f"{self.room.code} -> {self.get_status_display()} @ {self.timestamp:%d %b %H:%M}"
