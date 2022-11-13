import datetime
import json

from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django_nose.tools import *

from lib.tests import Suite101BaseTestCase
from lib.models import Follow
from profiles.models import UserImage, UserBlackList

@override_settings(CELERY_ALWAYS_EAGER=True)
class TestResetViews(Suite101BaseTestCase):
    def test_view_form(self):
        url = reverse('profile_request_reset')
        response = self.client.get(url)
        assert_template_used(response, 'profiles/request_reset.html')
