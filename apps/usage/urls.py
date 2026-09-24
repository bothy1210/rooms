from django.urls import path

from apps.usage import views

app_name = "usage"

urlpatterns = [
    path("room/<int:pk>/history/", views.room_usage_history, name="history"),
]
