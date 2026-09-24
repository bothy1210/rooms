from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "target", "previous_value", "new_value"]
    list_filter = ["action"]
    search_fields = ["target", "action"]
    readonly_fields = ["timestamp", "user", "action", "target", "previous_value", "new_value"]

    def has_add_permission(self, request):
        return False   # audit entries are only ever created by the system
