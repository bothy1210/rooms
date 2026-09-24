"""Usage history view for a room."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.rooms.models import Room


@login_required
def room_usage_history(request, pk):
    room = get_object_or_404(Room, pk=pk)
    logs = room.usage_logs.select_related("changed_by")[:50]
    return render(request, "usage/history.html", {"room": room, "logs": logs})
