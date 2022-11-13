import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.http import HttpRequest
from importlib import import_module
from lib.utils import queryset_iterator


def init_session(session_key):
    """
    Initialize same session as done for ``SessionMiddleware``.
    """
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key)


class Command(BaseCommand):
    help = 'usage: python manage.py logout_all_users'

    def handle(self, *args, **options):
        """
        Read all available users and all available not expired sessions. Then
        logout from each session.
        """
        now = datetime.datetime.now()
        request = HttpRequest()

        sessions = Session.objects.filter(expire_date__gt=now)
        print('Found %d not-expired session(s).' % len(sessions))

        for session in queryset_iterator(sessions):
            username = session.get_decoded().get('_auth_user_id')
            if not username:
                continue
            request.session = init_session(session.session_key)

            logout(request)
            print('Successfully logout %r user.' % username)

        print('All OK!')
