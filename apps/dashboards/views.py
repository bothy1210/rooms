"""Dashboard & reporting views."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.permissions import CAP_EXPORT_REPORTS
from apps.dashboards import selectors
from apps.dashboards.cache import cached_for_scope
from apps.dashboards.exports.excel import build_utilisation_xlsx
from apps.dashboards.exports.pdf import build_utilisation_pdf
from apps.dashboards.services import build_dashboard
from apps.rooms.services import RoomStatusService


@login_required
def home(request):
    """The scoped dashboard landing page (concept note 12)."""
    RoomStatusService.refresh_live_statuses_throttled()   # finished bookings free their room
    context = build_dashboard(request.user, request.GET.get("scope"))
    return render(request, "dashboards/dashboard.html", context)


@login_required
def reports(request):
    from apps.core.services import ScopeService

    scope = ScopeService.resolve(request.user, request.GET.get("scope"))
    context = {
        "scope": scope,
        "by_building": cached_for_scope("by_building", scope, lambda: selectors.utilisation_by_building(scope)),
        "by_department": cached_for_scope("by_department", scope,
                                          lambda: selectors.utilisation_by_department(scope)),
        "most_used": cached_for_scope("most_used", scope, lambda: selectors.most_used_rooms(scope)),
        "least_used": cached_for_scope("least_used", scope, lambda: selectors.least_used_rooms(scope)),
    }
    return render(request, "dashboards/reports.html", context)


@login_required
def export_pdf(request):
    from apps.core.services import ScopeService

    if not request.user.can(CAP_EXPORT_REPORTS):
        return render(request, "dashboards/forbidden.html", status=403)
    scope = ScopeService.resolve(request.user, request.GET.get("scope"))
    context = {
        "scope": scope,
        "stats": selectors.status_counts(scope),
        "by_building": selectors.utilisation_by_building(scope),
        "by_department": selectors.utilisation_by_department(scope),
    }
    return build_utilisation_pdf(context)


@login_required
def export_excel(request):
    from apps.core.services import ScopeService

    if not request.user.can(CAP_EXPORT_REPORTS):
        return render(request, "dashboards/forbidden.html", status=403)
    scope = ScopeService.resolve(request.user, request.GET.get("scope"))
    return build_utilisation_xlsx(selectors.utilisation_by_building(scope))
