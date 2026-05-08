from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """Ensure username is auto-set from email when not required."""

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.username:
            # Use email prefix as username
            user.username = user.email.split("@")[0][:150]
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        return settings.LOGIN_REDIRECT_URL


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Auto-set username from social account data."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.username:
            user.username = user.email.split("@")[0][:150]
            user.save(update_fields=["username"])
        return user
