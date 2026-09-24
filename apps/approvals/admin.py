from django.contrib import admin

from apps.approvals.models import ApprovalStep


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ["booking", "routed_to_department", "decision", "decided_by", "decided_at"]
    list_filter = ["decision", "routed_to_department"]
