"""Email rendering + delivery for notifications (HTML + plain-text fallback).

Delivery is fail-safe: every send is wrapped, its outcome recorded in
NotificationLog (sent/failed + error), and exceptions never propagate to the
request path. In prod each send runs in a background thread so the API response
is never blocked; NOTIFICATIONS_RUN_SYNC=True (tests / small deploys) runs inline.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.template.loader import render_to_string

from .models import Category

logger = logging.getLogger("notifications.email")


def _template_for(category):
    if str(category).startswith("MEMO"):
        return "emails/memo_action.html"
    if category in (Category.LEAVE_SUBMITTED, Category.LEAVE_APPROVED, Category.LEAVE_REJECTED):
        return "emails/leave_action.html"
    if category == Category.LEAVE_BALANCE_LOW:
        return "emails/balance_alert.html"
    return "emails/generic.html"


def _frontend(path=""):
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    if path and path.startswith("/"):
        return f"{base}{path}"
    return path or base


def _context(recipient_name, category, title, body, action_url, extra=None):
    ctx = {
        "recipient_name": recipient_name,
        "title": title,
        "body": body,
        "action_url": _frontend(action_url),
        "unsubscribe_url": _frontend("/notifications"),
        "category_label": dict(Category.choices).get(category, str(category)),
        # Branding (matches the PDF letterhead): hosted logo + org name.
        "logo_url": _frontend("/NIF.png"),
        "org_name": getattr(settings, "ORG_INFO", {}).get("name", "Nepal Internet Foundation"),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _record_log(recipient, recipient_email, category, object_id, subject, status, error=""):
    """Best-effort NotificationLog write. Runs in the (possibly background) send
    thread, so it opens/closes its own connection and never raises."""
    try:
        from .models import NotificationLog
        NotificationLog.objects.create(
            recipient=recipient, recipient_email=recipient_email or "",
            category=str(category), object_id=str(object_id or ""),
            subject=subject[:255], status=status, error=(error or "")[:2000],
        )
    except Exception:  # noqa: BLE001 - logging must never break delivery
        logger.exception("NotificationLog write failed (category=%s to=%s)", category, recipient_email)
    finally:
        # In a spawned thread Django won't auto-close the connection; leaking one
        # per email would exhaust the pool.
        if getattr(settings, "NOTIFICATIONS_RUN_SYNC", False) is False:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass


def send_notification_email(user_email, recipient_name, category, title, body, action_url,
                            extra=None, object_id="", recipient=None):
    """Render + send one notification email and record the outcome. Template
    rendering + SMTP touch no shared state, so this is safe in a background thread."""
    subject = f"[NIF] {title}"
    try:
        ctx = _context(recipient_name, category, title, body, action_url, extra)
        html = render_to_string(_template_for(category), ctx)
        text = render_to_string("emails/notification.txt", ctx)
        msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user_email])
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)  # we handle failures ourselves (log + swallow)
        _record_log(recipient, user_email, category, object_id, subject, "sent")
    except Exception as exc:  # noqa: BLE001 - never break the workflow on email
        logger.warning("Notification email failed to=%s category=%s: %s", user_email, category, exc)
        _record_log(recipient, user_email, category, object_id, subject, "failed", str(exc))


def dispatch_email(user, category, title, body, action_url, extra=None, object_id=""):
    args = (user.email, (user.get_full_name() or user.username), category, title, body, action_url)
    kwargs = {"extra": extra, "object_id": object_id, "recipient": user}
    if getattr(settings, "NOTIFICATIONS_RUN_SYNC", False):
        send_notification_email(*args, **kwargs)
        return
    threading.Thread(target=send_notification_email, args=args, kwargs=kwargs, daemon=True).start()
