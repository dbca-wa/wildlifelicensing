from django.conf import settings
from django.template.defaulttags import register


@register.filter
def get_url_filename(url):
    return url[url.rfind('/') + 1:]


@register.simple_tag
def get_privacy_policy_url():
    return settings.PRIVACY_POLICY_URL
