"""Approval workflow views — the pending queue and decision actions."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.approvals.services import ApprovalError, ApprovalService
from apps.bookings.models import Booking


@login_required
def pending_list(request):
    """Requests this user may action (scoped to their approval authority)."""
    pending = ApprovalService.pending_for(request.user).order_by("date", "start_time", "pk")
    page = Paginator(pending, 25).get_page(request.GET.get("page"))
    return render(request, "approvals/pending.html", {"pending": page, "page": page})


@login_required
@require_http_methods(["POST"])
def decide(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    approve = request.POST.get("action") == "approve"
    try:
        ApprovalService.decide(
            booking, user=request.user, approve=approve, comment=request.POST.get("comment", "")
        )
        verb = "approved" if approve else "rejected"
        messages.success(request, f"Booking BK-{booking.pk} {verb}. The requester has been notified.")
    except ApprovalError as exc:
        messages.error(request, str(exc))
    return redirect("approvals:pending")
