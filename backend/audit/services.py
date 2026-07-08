from .models import AuditLog

def log_action(actor, action, instance=None, changes=None, request=None):
    """
    Write an immutable AuditLog entry. Call this from perform_create/
    perform_update/perform_destroy or custom workflow actions in other apps -
    never mutate an AuditLog row afterward.
    """
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]

    return AuditLog.objects.create(
        actor=actor if actor is not None and getattr(actor, "is_authenticated", False) else None,
        action=action,
        content_object=instance,
        object_repr=str(instance) if instance is not None else "",
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
