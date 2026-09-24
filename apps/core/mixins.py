"""
View mixins for authentication and scope enforcement.

`ScopedListMixin` resolves the request's scope once and exposes it to both the
queryset and the template, so any list view (rooms, bookings, dashboards) can
be made scope-aware by mixing it in.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from apps.core.selectors import apply_room_scope
from apps.core.services import ScopeService


class ScopedListMixin(LoginRequiredMixin):
    """Resolve the current scope from ?scope= and apply it to the queryset.

    Subclasses set `scope_queryset_attr` to the queryset that should be
    filtered (defaults to the view's own get_queryset()).
    """

    scope_param = "scope"

    def get_scope(self):
        requested = self.request.GET.get(self.scope_param)
        return ScopeService.resolve(self.request.user, requested)

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_room_scope(qs, self.get_scope())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.get_scope()
        ctx["scope"] = scope
        ctx["available_scopes"] = ScopeService.available_scopes(self.request.user)
        return ctx


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only admin users (not read-only viewers) may reach the view."""

    def test_func(self):
        return getattr(self.request.user, "is_admin_user", False)


class CentralAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only central administrators may reach the view (e.g. room verification)."""

    def test_func(self):
        return getattr(self.request.user, "is_central_admin", False)
