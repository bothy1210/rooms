"""
Booking views — request form, live availability (HTMX), Find-a-Venue, calendar.

The live check returns an HTML partial so the booking form can validate a slot
without a full page reload, exactly like the prototype's inline conflict box.
"""
from datetime import date as date_cls
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.permissions import CAP_SUBMIT_BOOKING
from apps.bookings.forms import BookingRequestForm, VenueSearchForm
from apps.bookings.models import Booking, Purpose
from apps.bookings.selectors import find_venues_by_capacity
from apps.bookings.services import BookingService
from apps.rooms.models import Room


@login_required
def booking_create(request):
    form = BookingRequestForm(request.POST or None)
    if request.method == "POST":
        if not request.user.can(CAP_SUBMIT_BOOKING):
            messages.error(request, "You are not permitted to submit bookings.")
            return redirect("bookings:list")
        if form.is_valid():
            data = form.cleaned_data
            check = BookingService.check_availability(
                room=data["room"], date=data["date"], start=data["start_time"],
                end=data["end_time"], attendance=data["attendance"], purpose=data["purpose"],
            )
            if check.ok:
                booking = BookingService.create_request(
                    room=data["room"], date=data["date"], start=data["start_time"],
                    end=data["end_time"], purpose=data["purpose"], attendance=data["attendance"],
                    requester=request.user, requester_name=data["requester_name"],
                    requester_dept=data["requester_dept"], equipment_note=data["equipment_note"],
                )
                messages.success(
                    request,
                    f"Booking {booking.pk} submitted and routed to {booking.room.department} for approval.",
                )
                return redirect("bookings:list")
            messages.error(request, "Requested slot is not available — see the conflict details.")
    return render(request, "bookings/booking_form.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def check_availability(request):
    """HTMX endpoint: returns the availability/conflict partial for the form."""
    form = BookingRequestForm(request.POST)
    if not form.is_valid():
        return render(request, "bookings/partials/_availability_result.html", {"form_errors": form.errors})
    d = form.cleaned_data
    result = BookingService.check_availability(
        room=d["room"], date=d["date"], start=d["start_time"],
        end=d["end_time"], attendance=d["attendance"], purpose=d["purpose"],
    )
    return render(request, "bookings/partials/_availability_result.html", {"result": result, "room": d["room"]})


@login_required
def find_venue(request):
    """Capacity-first, university-wide venue search."""
    form = VenueSearchForm(request.GET or None)
    venues, searched = [], False
    if request.GET and form.is_valid():
        searched = True
        d = form.cleaned_data
        venues = find_venues_by_capacity(
            attendance=d["attendance"], purpose=d["purpose"],
            date=d.get("date"), start=d.get("start_time"), end=d.get("end_time"),
        )
    # Flag which venues belong to another unit (for the "cross-unit" badge).
    my_dept_id = getattr(request.user, "department_id", None)
    for v in venues:
        v.cross_unit = my_dept_id is not None and v.department_id != my_dept_id
    return render(request, "bookings/find_venue.html", {
        "form": form, "venues": venues, "searched": searched,
    })


@login_required
def booking_list(request):
    bookings = Booking.objects.select_related("room", "room__department").order_by("-date", "start_time", "pk")
    page = Paginator(bookings, 25).get_page(request.GET.get("page"))
    return render(request, "bookings/list.html", {"bookings": page, "page": page})


@login_required
def calendar(request):
    """Month calendar of approved/pending bookings."""
    today = date_cls.today()
    try:
        first = date_cls(int(request.GET.get("year", today.year)), int(request.GET.get("month", today.month)), 1)
    except ValueError:   # junk or out-of-range ?year= / ?month=
        first = today.replace(day=1)
    next_first = (first + timedelta(days=32)).replace(day=1)
    # A date range (not date__year/date__month) lets PostgreSQL use the date index.
    bookings = (
        Booking.objects.filter(date__gte=first, date__lt=next_first)
        .select_related("room").order_by("date", "start_time", "pk")
    )
    page = Paginator(bookings, 50).get_page(request.GET.get("page"))
    return render(request, "bookings/calendar.html", {
        "year": first.year, "month": first.month, "bookings": page, "page": page,
    })
