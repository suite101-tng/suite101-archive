import json
import mock

from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django_nose.tools import *

from lib.tests import Suite101BaseTestCase
from django.contrib.contenttypes.models import ContentType
from articles.models import *
from suites.models import *
from lib.models import *

@override_settings(CELERY_ALWAYS_EAGER=True)
class TestSuites(Suite101BaseTestCase):
    def setUp(self):
        User = get_user_model()
        self.redis = RedisObject()
        self.redis.redis.flushall()
        super(TestSuites, self).setUp()
        self.articles = []

        for i in range(5):
            self.articles.append(
                Article.objects.create(
                    author=self.user,
                    slug='some-slug-%s-that-is-unique' % i,
                    title='Yup',
                    body='Yes',
                    status=Article.STATUS.published
                )
            )
        self.user2 = User.objects.create_user('test2@test.com', 'foobar')
        self.user2.is_active = True
        self.user2.save()

        self.moderator = User.objects.create_user('moderators@test.com', 'foobar')
        self.moderator.is_active = True
        self.moderator.is_moderator = True
        self.moderator.save()

        self.suite = Suite.objects.create(owner=self.user, name='test suite')

        self._test_login()

    def tearDown(self):
        self.redis.redis.flushall()
        del self.redis
        del self.articles
        del self.user
        del self.user2

class TestSuiteTasks(Suite101BaseTestCase):
    def setUp(self):
        super(TestSuiteTasks, self).setUp()
        self.suite = Suite.objects.create(owner=self.user, name='test suite')
        self.redis = RedisObject()
        self.redis.redis.flushall()

    def tearDown(self):
        del self.suite











