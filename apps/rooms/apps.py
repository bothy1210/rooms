from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rooms"
    verbose_name = "Room Inventory"

    def ready(self):
        # Connect the status-change -> audit signals.
        from apps.rooms import signals  # noqa: F401
