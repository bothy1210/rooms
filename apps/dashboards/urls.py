from django.urls import path

from apps.dashboards import views

app_name = "dashboards"

urlpatterns = [
    path("", views.home, name="home"),
    path("reports/", views.reports, name="reports"),
    path("reports/export/pdf/", views.export_pdf, name="export_pdf"),
    path("reports/export/excel/", views.export_excel, name="export_excel"),
]
