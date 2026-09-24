"""Stub — captures the current user for audit signals. Full version in the audit app build."""
import threading

_local = threading.local()


def get_current_user():
    return getattr(_local, "user", None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = getattr(request, "user", None)
        return self.get_response(request)
