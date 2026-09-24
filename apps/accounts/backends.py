"""
Optional Omhare directory integration.

By default the system uses Django's ModelBackend (self-contained accounts), so
it can go live independently. When the university is ready to federate with the
existing Omhare University Information System, enable one of these backends in
settings AUTHENTICATION_BACKENDS and users will sign in with the same username
they use elsewhere.

This file is a documented scaffold — the actual LDAP bind is left commented so
the project runs without django-auth-ldap installed.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


class OmhareLDAPBackend:
    """Skeleton LDAP/SSO backend.

    To activate:
      1. pip install django-auth-ldap  (already listed, commented, in requirements.txt)
      2. Configure AUTH_LDAP_SERVER_URI / bind settings in production.py
      3. Add "apps.accounts.backends.OmhareLDAPBackend" to AUTHENTICATION_BACKENDS
      4. Implement the bind + attribute mapping below.

    Role/scope mapping strategy: read the user's directory groups and map them
    to (role, department, faculty) so central IT manages membership once, in the
    directory, rather than in this system.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):  # pragma: no cover
        # Example flow (pseudo-code — enable with django-auth-ldap):
        #
        #   conn = ldap_bind(username, password)
        #   if not conn:
        #       return None
        #   attrs = conn.search(username)
        #   user, _ = User.objects.get_or_create(username=username, defaults={...})
        #   self._sync_role_and_scope(user, attrs)
        #   return user
        return None

    def get_user(self, user_id):  # pragma: no cover
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    # def _sync_role_and_scope(self, user, attrs):
    #     """Map directory groups → role, department, faculty."""
    #     ...
