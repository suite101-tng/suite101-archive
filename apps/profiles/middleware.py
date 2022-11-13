import datetime

LAST_SEEN_DELTA = 30

class LastSeenMiddleware(object):
    def update_last_seen(self, request, now):
        request.session['last_seen'] = now
        request.user.last_seen = now
        request.user.save()

    def process_request(self, request):
        # import pdb; pdb.set_trace()
        if request.user.is_authenticated():
            now = datetime.datetime.now()

            # check to see if the current user session has a last_seen time set
            if 'last_seen' in request.session:
                last_seen = request.session['last_seen']

                # if this request occurs more than XX minutes later than last seen, we update
                if last_seen < now - datetime.timedelta(minutes=LAST_SEEN_DELTA):
                    self.update_last_seen(request, now)
            else:
                self.update_last_seen(request, now)

        return None

# -*- coding: utf-8 -*-
import six

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.utils.http import urlquote

from social.exceptions import SocialAuthBaseException, NotAllowedToDisconnect

class SocialAuthExceptionMiddleware(object):
    """Middleware that handles Social Auth AuthExceptions by providing the user
    with a message, logging an error, and redirecting to some next location.
    By default, the exception message itself is sent to the user and they are
    redirected to the location specified in the SOCIAL_AUTH_LOGIN_ERROR_URL
    setting.
    This middleware can be extended by overriding the get_message or
    get_redirect_uri methods, which each accept request and exception.
    """
    def process_exception(self, request, exception):
        # import pdb; pdb.set_trace()
        strategy = getattr(request, 'social_strategy', None)
        if strategy is None or self.raise_exception(request, exception):
            return

        if isinstance(exception, SocialAuthBaseException):
            backend = getattr(request, 'backend', None)
            backend_name = getattr(backend, 'name', 'unknown-backend')

            message = self.get_message(request, exception)
            url = self.get_redirect_uri(request, exception, backend_name)
            try:
                messages.error(request, message,
                               extra_tags='social-auth ' + backend_name)
            except MessageFailure:
                url += ('?' in url and '&' or '?') + \
                       'message={0}&backend={1}'.format(urlquote(message),
                                                        backend_name)
            return redirect(url)

    def raise_exception(self, request, exception):
        return False
        strategy = getattr(request, 'social_strategy', None)
        if strategy is not None:
            return strategy.setting('RAISE_EXCEPTIONS', settings.DEBUG)

    def get_message(self, request, exception):
        return six.text_type(exception)

    def get_redirect_uri(self, request, exception, backend_name):
        strategy = getattr(request, 'social_strategy', None)
        if isinstance(exception, NotAllowedToDisconnect):
            return reverse('profile_set_password', kwargs={'backend': backend_name})
        return strategy.setting('SOCIAL_AUTH_LOGIN_ERROR_URL')

