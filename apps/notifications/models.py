"""Notification model - in-app messages (concept note 7.7)."""
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, related_name="notifications"
    )
    message = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{'[read] ' if self.is_read else ''}{self.message[:50]}"
