"""Authentication and user-administration views."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import UserCreateForm, UsernameLoginForm
from apps.accounts.models import User
from apps.accounts.permissions import CAP_MANAGE_USERS
from apps.audit.services import log_change


@never_cache  # a cached copy would carry a CSRF token that is rotated on login/logout
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboards:home")
    form = UsernameLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get("next") or reverse("dashboards:home"))
    return render(request, "accounts/login.html", {"form": form})


def csrf_failure(request, reason=""):
    """A stale login form (Back button, second tab) just gets a fresh login page."""
    if request.path == reverse("accounts:login"):
        return redirect("accounts:login")
    return default_csrf_failure(request, reason=reason)


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def user_list(request):
    """Central-admin user administration (read-only viewers can't reach it)."""
    if not request.user.can(CAP_MANAGE_USERS):
        return render(request, "accounts/forbidden.html", status=403)
    users = User.objects.select_related("department", "faculty").all()
    return render(request, "accounts/user_list.html", {"users": users})


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    """Central admin adds a new user account."""
    if not request.user.can(CAP_MANAGE_USERS):
        return render(request, "accounts/forbidden.html", status=403)
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_change("user.create", user, new=user.get_role_display(), user=request.user)
        messages.success(request, f"User {user.username} ({user.get_role_display()}) was added.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form})
