from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("mark-read/", views.mark_read, name="mark_read"),
]
