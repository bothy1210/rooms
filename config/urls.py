"""Root URL router — includes each app's own urls.py under a namespace."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboards.urls")),          # "/" → dashboard home
    path("accounts/", include("apps.accounts.urls")),
    path("rooms/", include("apps.rooms.urls")),
    path("usage/", include("apps.usage.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("approvals/", include("apps.approvals.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("audit/", include("apps.audit.urls")),
]

# Serve uploaded room photos in development (Nginx handles this in production).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass
