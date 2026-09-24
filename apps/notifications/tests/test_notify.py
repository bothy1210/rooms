"""Tests for the notification service."""
import pytest
from django.core import mail

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import mark_all_read, notify, unread_count

pytestmark = pytest.mark.django_db


def test_notify_creates_in_app_record():
    user = User.objects.create_user("R1", full_name="Test", email="")
    note = notify(user=user, message="Booking approved")
    assert note is not None
    assert Notification.objects.filter(user=user).count() == 1


def test_notify_with_email_also_sends_email():
    user = User.objects.create_user("R2", full_name="Test", email="test@uz.ac.zw")
    notify(user=user, message="Booking approved")
    assert len(mail.outbox) == 1
    assert "test@uz.ac.zw" in mail.outbox[0].to


def test_notify_none_user_is_safe():
    assert notify(user=None, message="system event") is None


def test_unread_count_and_mark_read():
    user = User.objects.create_user("R3", full_name="Test")
    notify(user=user, message="one")
    notify(user=user, message="two")
    assert unread_count(user) == 2
    mark_all_read(user)
    assert unread_count(user) == 0
