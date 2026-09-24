"""
Template context processors.

These make a couple of values available in every template without each view
having to pass them — the institution name (for the Omhare-style header) and
the current dashboard scope (for the scope switcher partial).
"""
from django.conf import settings

from apps.core.services import ScopeService


def institution(request):
    """Expose the institution name to the base layout header."""
    return {"INSTITUTION_NAME": getattr(settings, "INSTITUTION_NAME", "University of Zimbabwe")}


def current_scope(request):
    """Expose the resolved scope + available scopes for the scope switcher.

    Safe for anonymous users (login page): returns empty values.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"current_scope": None, "available_scopes": []}
    requested = request.GET.get("scope")
    return {
        "current_scope": ScopeService.resolve(user, requested),
        "available_scopes": ScopeService.available_scopes(user),
    }
