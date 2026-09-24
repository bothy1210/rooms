from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboards"
    verbose_name = "Dashboards & Reporting"

    def ready(self):
        from apps.dashboards import signals  # noqa: F401  (connects the cache-clearing receivers)
