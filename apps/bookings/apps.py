from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bookings"
    verbose_name = "Bookings & Scheduling"

    def ready(self):
        from apps.bookings import signals  # noqa: F401
