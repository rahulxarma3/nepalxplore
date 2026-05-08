def subscription_status(request):
    """Makes subscription state available in every template."""
    if request.user.is_authenticated:
        sub = getattr(request.user, "subscription", None)
        return {
            "is_subscribed": sub.is_active if sub else False,
            "subscription": sub,
            "days_remaining": sub.days_remaining if sub else 0,
        }
    return {
        "is_subscribed": False,
        "subscription": None,
        "days_remaining": 0,
    }
