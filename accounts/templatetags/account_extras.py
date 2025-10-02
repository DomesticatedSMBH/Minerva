from django import template
from django.conf import settings

try:
    from allauth.socialaccount.models import SocialApp
except Exception:  # pragma: no cover - allauth always available but be safe
    SocialApp = None

register = template.Library()


@register.simple_tag
def google_login_available():
    """Return True when a Google social application is configured for the current site."""
    if SocialApp is None:
        return False
    return SocialApp.objects.filter(provider="google", sites__id=getattr(settings, "SITE_ID", 1)).exists()
