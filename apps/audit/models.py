"""Audit trail model - records who changed what, when, and old -> new value."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_entries"
    )
    action = models.CharField(max_length=80)          # e.g. "Status change", "Room verified"
    target = models.CharField(max_length=200)         # e.g. "UZ-LT-101 - Great Hall"
    previous_value = models.CharField(max_length=200, blank=True)
    new_value = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["-timestamp"])]

    def __str__(self):
        return f"{self.timestamp:%d %b %H:%M} - {self.action} - {self.target}"
