from django.urls import path

from apps.rooms import views

app_name = "rooms"

urlpatterns = [
    path("", views.inventory, name="inventory"),
    path("<int:pk>/", views.room_detail, name="detail"),
    path("<int:pk>/status/", views.update_status, name="update_status"),
    path("register/", views.register_room, name="register"),
    path("draft/<int:pk>/verify/", views.verify_room, name="verify"),
]
