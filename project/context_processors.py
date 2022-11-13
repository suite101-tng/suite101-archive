from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

from moderation.sets import AdminHijackKey
from hijack.signals import hijack_started, hijack_ended

def _hijack_on(sender, hijacker_id, hijacked_id, **kwargs):
    print('hij on')
    try:
        AdminHijackKey(hijacker_id).set_key(hijacked_id)
    except Exception as e:
        print('problem setting key: %s' % e)

def _hijack_off(sender, hijacker_id, hijacked_id, **kwargs):
    AdminHijackKey(hijacker_id).clear()

def settings(request):
    """
    Adds the settings specified in settings.TEMPLATE_VISIBLE_SETTINGS to
    the request context.
    """
    if request.user.is_authenticated() and request.user.is_moderator:
        hijack_started.connect(_hijack_on)
        hijack_ended.connect(_hijack_off)

    new_settings = {}
    for attr in django_settings.TEMPLATE_VISIBLE_SETTINGS:
        try:
            new_settings[attr] = getattr(django_settings, attr)
        except AttributeError:
            m = "TEMPLATE_VISIBLE_SETTINGS: '{0}' does not exist".format(attr)
            raise ImproperlyConfigured(m)
    return new_settings

def get_client_ip(request):
    from lib.utils import strip_non_ascii
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return {"client_ip": strip_non_ascii(ip)}

def login_disabled(request):
    disabled = django_settings.LOGIN_DISABLED if django_settings.LOGIN_DISABLED else ''
    return {"login_disabled": disabled}

def get_user_agent(request):
    from lib.utils import strip_non_ascii
    return {"user_agent": strip_non_ascii(request.META.get('HTTP_USER_AGENT', ''))}

def get_initial_referer(request):
    from lib.utils import strip_non_ascii
    return {"initial_referer": strip_non_ascii(request.META.get('HTTP_REFERER', ''))}

def accepted_terms(request):
    if not request.user.is_authenticated():
        return {'accepted_terms': True}
    return {'accepted_terms': request.user.accepted_terms}