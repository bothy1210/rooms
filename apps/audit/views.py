"""Audit trail view - filterable log of all recorded changes (concept note 7.8)."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from apps.audit.models import AuditLog


@login_required
def audit_trail(request):
    entries = AuditLog.objects.select_related("user")
    action = request.GET.get("action", "").strip()
    if action:
        entries = entries.filter(action__icontains=action)
    page = Paginator(entries, 30).get_page(request.GET.get("page"))
    return render(request, "audit/trail.html", {"page": page, "action": action})
