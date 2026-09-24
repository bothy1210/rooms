from django.urls import path

from apps.approvals import views

app_name = "approvals"

urlpatterns = [
    path("", views.pending_list, name="pending"),
    path("<int:pk>/decide/", views.decide, name="decide"),
]
