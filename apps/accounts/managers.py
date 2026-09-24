"""
Custom user manager.

Users are identified by a username. It is stored as typed and looked up
without regard to case, so "TMoyo" and "tmoyo" are the same account.
"""
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the username-based User model."""

    use_in_migrations = True

    def get_by_natural_key(self, username):
        # Sign-in is case-insensitive; the create form keeps usernames unique that way.
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": (username or "").strip()})

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Users must have a username.")
        username = username.strip()
        email = extra_fields.pop("email", "")
        if email:
            email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_central_admin", True)
        extra_fields.setdefault("role", "central_admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(username, password, **extra_fields)
