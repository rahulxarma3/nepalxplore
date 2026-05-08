"""
apps/accounts/signals.py

Hooks into allauth signals to fire welcome notifications on new user signup.
"""
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added


@receiver(user_signed_up)
def on_user_signed_up(request, user, **kwargs):
    """Fire welcome notification when a new user registers."""
    from apps.core.models import Notification
    Notification.objects.create(
        user=user,
        notification_type="welcome",
        title="Welcome to NepaXplore! 🏔️",
        body="Discover Nepal's history, culture, and trekking routes through guided video content. Subscribe to unlock everything.",
        link="/subscribe/",
    )


@receiver(social_account_added)
def on_social_account_added(request, sociallogin, **kwargs):
    """Fire welcome notification when a user connects Google OAuth."""
    user = sociallogin.user
    # Only fire if user was just created (not an existing user connecting Google)
    if getattr(user, "_allauth_account_created", False):
        from apps.core.models import Notification
        Notification.objects.create(
            user=user,
            notification_type="welcome",
            title="Welcome to NepaXplore! 🏔️",
            body="Signed in with Google. Subscribe to unlock all destinations, trekking guides and the full video library.",
            link="/subscribe/",
        )
