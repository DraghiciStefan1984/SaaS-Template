from .models import AuditEventStatus, AuditLog


def get_request_ip_address(request):
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_request_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def get_request_id(request):
    if request is None:
        return ""
    return (
        getattr(request, "request_id", "")
        or request.META.get("HTTP_X_REQUEST_ID")
        or request.META.get("HTTP_X_CORRELATION_ID")
        or ""
    )[:120]


def log_audit_event(
    *,
    action,
    organization=None,
    user=None,
    request=None,
    category="",
    status=AuditEventStatus.SUCCEEDED,
    target_entity_type="",
    target_entity_id="",
    metadata=None,
):
    if user is None and request is not None and getattr(request, "user", None):
        user = request.user if request.user.is_authenticated else None

    return AuditLog.objects.create(
        organization=organization,
        user=user,
        action=action,
        category=category,
        status=status,
        target_entity_type=target_entity_type,
        target_entity_id=str(target_entity_id) if target_entity_id else "",
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
        request_id=get_request_id(request),
        metadata=metadata or {},
    )
