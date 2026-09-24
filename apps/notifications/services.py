"""
Notification service.

`notify()` creates an in-app notification and, when the recipient has an email
address, also sends an email. `send_email()` wraps Django's mail so the transport
(console in dev, SMTP in production) is decided entirely by settings — no caller
needs to know which.
"""
from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.models import Notification


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a single email. Returns True if at least one message was sent."""
    if not to_email:
        return False
    sent = send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "roomsys@uz.ac.zw"),
        recipient_list=[to_email],
        fail_silently=True,  # never break a booking flow because SMTP hiccuped
    )
    return bool(sent)


def notify(*, user, message: str, email_subject: str = "UZ Room System") -> Notification | None:
    """Create an in-app notification and mirror it by email if possible.

    `user` may be None (e.g. a system-level event) — in that case no record is
    created but the call is still safe.
    """
    if user is None:
        return None
    note = Notification.objects.create(user=user, message=message)
    if getattr(user, "email", ""):
        send_email(user.email, email_subject, message)
    return note


def unread_count(user) -> int:
    if not getattr(user, "is_authenticated", False):
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_all_read(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)
