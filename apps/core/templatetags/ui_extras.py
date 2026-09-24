"""
UI helper tags that render the same visual components used in the HTML
prototype (status pills, capacity tags, suitability tags), so templates stay
clean and the styling stays consistent.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Maps a room/booking status to a CSS pill class (defined in static/css/app.css).
_STATUS_CLASS = {
    "available": "p-available",
    "in_use": "p-inuse",
    "booked": "p-booked",
    "maintenance": "p-unavail",
    "cleaning": "p-unavail",
    "closed": "p-unavail",
    "pending": "p-pending",
    "approved": "p-approved",
    "rejected": "p-rejected",
    "cancelled": "p-cancelled",
    "draft": "p-pending",
}


@register.simple_tag
def status_pill(value, label=None):
    """Render a coloured status pill: {% status_pill room.status room.get_status_display %}"""
    key = str(value).lower().replace(" ", "_")
    css = _STATUS_CLASS.get(key, "p-cancelled")
    text = label or str(value).replace("_", " ").title()
    return mark_safe(f'<span class="pill {css}">{text}</span>')


@register.simple_tag
def capacity_tag(capacity):
    """Render a small monospace capacity chip."""
    return mark_safe(f'<span class="cap-tag">{capacity}</span>')


@register.simple_tag
def suit_tag(name):
    """Render a suitability tag chip (e.g. 'Examinations')."""
    return mark_safe(f'<span class="suit-tag">{name}</span>')


@register.filter
def pct(part, whole):
    """Percentage helper for dashboards: {{ available|pct:total }} → '33.9'."""
    try:
        whole = float(whole)
        if whole == 0:
            return "0.0"
        return f"{float(part) / whole * 100:.1f}"
    except (ValueError, TypeError):
        return "0.0"
