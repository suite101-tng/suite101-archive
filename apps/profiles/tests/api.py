from django.contrib.auth import get_user_model
from django_nose.tools import *

from lib.tests import Suite101ResourceBaseTestCase
from profiles.models import UserImage

class UserResourceTest(Suite101ResourceBaseTestCase):
    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.detail_url = '/api/v1/user/{0}/'.format(self.user.slug)
        self.post_data = {
            'first_name': 'First',
            'last_name': 'Last',
            'by_line': 'Yes I am me',
            'personal_url': 'www.example.com'
        }

    def tearDown(self):
        del self.detail_url
        del self.post_data









