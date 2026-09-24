"""Notification views - list and mark-as-read."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.notifications.models import Notification
from apps.notifications.services import mark_all_read


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def mark_read(request):
    mark_all_read(request.user)
    return redirect("notifications:list")
