from django.contrib import admin

from apps.bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "purpose", "date", "start_time", "end_time", "attendance", "status"]
    list_filter = ["status", "purpose", "date"]
    search_fields = ["room__code", "requester_name"]
    date_hierarchy = "date"
