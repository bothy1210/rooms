from django.urls import path

from apps.bookings import views

app_name = "bookings"

urlpatterns = [
    path("", views.booking_list, name="list"),
    path("new/", views.booking_create, name="create"),
    path("check/", views.check_availability, name="check"),
    path("find-venue/", views.find_venue, name="find_venue"),
    path("calendar/", views.calendar, name="calendar"),
]
