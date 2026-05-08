def unread_notifications(request):
    """
    Injects unread_notif_count into every template context.
    Used by the nav bell badge without an extra HTMX call on first render.
    """
    if request.user.is_authenticated:
        from apps.core.models import Notification
        try:
            count = Notification.objects.filter(
                user=request.user,
                is_read=False,
            ).count()
        except Exception:
            count = 0
        return {"unread_notif_count": count}
    return {"unread_notif_count": 0}
