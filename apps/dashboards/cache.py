"""
Short-lived cache for dashboard and report figures.

The aggregates behind the stat cards, charts and report tables are the same
for everyone looking at the same scope, so they are computed once and shared.
Any room or booking change bumps a version number, which makes every cached
figure stale at once (see signals.py); DASHBOARD_CACHE_SECONDS only bounds
staleness from changes that bypass model signals, such as bulk updates.
"""
from django.conf import settings
from django.core.cache import cache

VERSION_KEY = "dashboards:version"


def _version() -> int:
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.add(VERSION_KEY, 1, timeout=None)
        version = cache.get(VERSION_KEY, 1)
    return version


def cached_for_scope(name, scope, compute):
    """Return compute() for this scope, from the cache when it is fresh."""
    key = (f"dashboards:v{_version()}:{name}:"
           f"{scope.key}:{scope.department_id or '-'}:{scope.faculty_id or '-'}")
    return cache.get_or_set(key, compute, timeout=settings.DASHBOARD_CACHE_SECONDS)


def invalidate():
    """Make every cached dashboard/report figure stale."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:   # no version stored yet: nothing is cached under it
        cache.add(VERSION_KEY, 1, timeout=None)
