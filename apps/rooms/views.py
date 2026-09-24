"""
Room views — inventory, detail drawer, registration and verification.

Views stay thin: they check capability + scope, then delegate to the services
and selectors. Rendering the actual templates is left to the presentation
build; these return the right context and enforce the rules.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.permissions import CAP_REGISTER_ROOM, CAP_VERIFY_ROOM
from apps.core.services import ScopeService
from apps.rooms.forms import RoomDraftForm, StatusUpdateForm
from apps.rooms.models import DraftStatus, Room, RoomDraft
from apps.rooms.selectors import search_rooms
from apps.rooms.services import (
    RoomRegistrationError,
    RoomRegistrationService,
    RoomStatusService,
)


@login_required
def inventory(request):
    """Scoped, filterable room inventory (paginated)."""
    RoomStatusService.refresh_live_statuses_throttled()   # finished bookings free their room
    scope = ScopeService.resolve(request.user, request.GET.get("scope"))
    rooms = search_rooms(
        scope=scope,
        query=request.GET.get("q", "").strip(),
        building_id=request.GET.get("building") or None,
        room_type_id=request.GET.get("type") or None,
        status=request.GET.get("status", ""),
        min_capacity=int(request.GET.get("min_capacity") or 0),
    )
    page = Paginator(rooms, 12).get_page(request.GET.get("page"))
    return render(request, "rooms/inventory.html", {
        "page": page,
        "scope": scope,
        "available_scopes": ScopeService.available_scopes(request.user),
    })


@login_required
def room_detail(request, pk):
    """Room detail drawer (HTMX-loaded). Includes whether the user may edit."""
    room = get_object_or_404(
        Room.objects.select_related("building", "floor", "department", "room_type"), pk=pk
    )
    return render(request, "rooms/partials/_room_drawer.html", {
        "room": room,
        "can_edit": request.user.can_update_status(room),
        "status_form": StatusUpdateForm(initial={"status": room.status}),
    })


@login_required
@require_http_methods(["POST"])
def update_status(request, pk):
    room = get_object_or_404(Room, pk=pk)
    # Role + scope check: only in-scope admins may change this room.
    if not request.user.can_update_status(room):
        messages.error(request, "This room is outside your scope — status is read-only for you.")
        return redirect("rooms:inventory")
    form = StatusUpdateForm(request.POST)
    if form.is_valid():
        RoomStatusService.update_status(room, form.cleaned_data["status"])  # audit via signal
        messages.success(request, f"{room.name} status updated to “{room.get_status_display()}”.")
    return redirect("rooms:inventory")


@login_required
@require_http_methods(["GET", "POST"])
def register_room(request):
    """Submit a room Draft. Any admin may register; verification is separate."""
    if not request.user.can(CAP_REGISTER_ROOM):
        return render(request, "rooms/forbidden.html", status=403)
    form = RoomDraftForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            # One transaction: newly typed buildings/types/departments are not kept if the draft fails.
            with transaction.atomic():
                RoomRegistrationService.submit_draft(submitted_by=request.user, **form.draft_fields())
            messages.success(request, "Room submitted as a Draft. It becomes bookable once verified.")
            return redirect("rooms:register")
        except RoomRegistrationError as exc:
            messages.error(request, str(exc))
    pending = RoomDraft.objects.filter(status=DraftStatus.DRAFT).select_related(
        "building", "floor", "department", "room_type"
    )
    return render(request, "rooms/register.html", {
        "form": form,
        "pending": pending,
        "can_verify": request.user.can(CAP_VERIFY_ROOM),
    })


@login_required
@require_http_methods(["POST"])
def verify_room(request, pk):
    """Central admin verifies a Draft → creates a Room with an official code."""
    if not request.user.can(CAP_VERIFY_ROOM):
        messages.error(request, "Only central administration can verify rooms.")
        return redirect("rooms:register")
    draft = get_object_or_404(RoomDraft, pk=pk)
    try:
        room = RoomRegistrationService.verify(draft, verified_by=request.user)
        messages.success(request, f"{draft.name} verified — issued code {room.code}. It is now bookable.")
    except RoomRegistrationError as exc:
        messages.error(request, str(exc))
    return redirect("rooms:register")
