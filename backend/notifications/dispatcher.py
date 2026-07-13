"""
Central notification dispatcher.

    notify(user, category, title, body, action_url, idempotency_key=None)

Respects the recipient's NotificationPreference (in-app + email, per category),
creates the in-app record, and enqueues email delivery. An idempotency key
collapses duplicate notifications for the same recipient.
"""
from . import emails
from .models import Category, Notification, NotificationPreference


def get_preference(user, category):
    """Return the user's preference for a category, or a sensible default
    (everything on except the opt-in weekly digest email)."""
    pref = NotificationPreference.objects.filter(user=user, category=category).first()
    if pref:
        return pref
    email_default = category != Category.WEEKLY_DIGEST
    return NotificationPreference(user=user, category=category, in_app_enabled=True, email_enabled=email_default)


def notify(user, category, title, body="", action_url="", idempotency_key=None,
           email_context=None, object_id=""):
    """
    email_context: optional dict merged into the HTML email template context
    (e.g. structured leave detail: status badge, BS+AD dates, days, remarks).
    object_id: source-object reference (e.g. leave UUID) recorded in NotificationLog.
    """
    if user is None or not getattr(user, "is_active", True):
        return None

    pref = get_preference(user, category)
    notif = None

    if pref.in_app_enabled:
        if idempotency_key:
            notif, created = Notification.objects.get_or_create(
                recipient=user, idempotency_key=idempotency_key,
                defaults={"category": category, "title": title, "body": body, "action_url": action_url or ""},
            )
            if not created:
                return notif  # already delivered; do not re-send email either (dedup)
        else:
            notif = Notification.objects.create(
                recipient=user, category=category, title=title, body=body, action_url=action_url or "",
            )

    if pref.email_enabled and getattr(user, "email", ""):
        if notif is not None:
            # Optimistically flag in the main thread so the email worker never
            # needs a DB connection (avoids sqlite lock contention under tests).
            Notification.objects.filter(pk=notif.pk).update(is_email_sent=True)
        emails.dispatch_email(user, category, title, body, action_url or "",
                              extra=email_context, object_id=object_id)

    return notif
