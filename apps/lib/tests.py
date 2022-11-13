from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY
from django.core.urlresolvers import reverse

from tastypie.test import ResourceTestCase, TestApiClient
from tastypie.serializers import Serializer
from lib.sets import RedisObject
from lib.enums import *
from lib.utils import set_unique_top_level_url, set_unique_suite_url

class Suite101ResourceBaseTestCase(ResourceTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('test@test.com', 'foobar')
        self.user.activate_user()
        self.user.save()

        self.api_client = TestApiClient()
        self.serializer = Serializer()
        self.get_credentials()

        self.moderator = User.objects.create_user(email='mod@suite.io', password='foobar')
        self.moderator.is_moderator = True
        self.moderator.is_active = True
        self.moderator.save()

    def tearDown(self):
        del self.user
        del self.moderator
       
    def get_credentials(self):
        result = self.api_client.client.login(email=self.user.email,
                                               password='foobar')
        return result

    def login_moderator(self):
        self.api_client.client.logout()
        self.api_client.client.login(email=self.moderator.email,
                                                password='foobar')


class Suite101BaseTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.redis = RedisObject()
        self.redis.redis.flushall()

        self.user = User.objects.create_user('test@test.com', 'foobar')
        self.user.slug = 'test-user'
        self.user.activate_user()
        self.user.save()

    def tearDown(self):
        del self.user
        self.redis.redis.flushall()
        del self.redis

    def assertRedirectsNoFollow(self, response, expected_url):
        self.assertEqual(response._headers['location'], ('Location', 'http://testserver' + expected_url))
        self.assertEqual(response.status_code, 302)

    def _post_ajax(self, url, data):
        return self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def _test_login(self, ajax=False, email=None, password=None):
        if not email:
            email = self.user.email
        if not password:
            password = 'foobar'

        url = reverse('login')
        data = {
            'email': email,
            'password': password
        }
        if ajax:
            response = self._post_ajax(url, data)
            self.assertEqual(response.status_code, 200)
        else:
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)

        self.assertTrue(SESSION_KEY in self.client.session)


class TestUniqueURLs(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('test@test.com', 'foobar')
        self.user.slug = 'tester-testerson'
        self.user.save()

    def tearDown(self):
        del self.user

    def test_unique_no_match(self):
        test_slug = 'no-match'
        new_slug = set_unique_top_level_url(test_slug)
        self.assertEqual(test_slug, new_slug)

    def test_matches_user(self):
        test_slug = 'tester-testerson'
        new_slug = set_unique_top_level_url(test_slug)
        self.assertEqual(new_slug, 'tester-testerson-1')

    def test_matches_two_users(self):
        User = get_user_model()
        user = User.objects.create_user('test2@test.com', 'foobar')
        user.slug = 'tester-testerson-1'
        user.save()
        test_slug = 'tester-testerson'
        new_slug = set_unique_top_level_url(test_slug)
        self.assertEqual(new_slug, 'tester-testerson-2')

    def test_matches_top_level_url(self):
        test_slug = 'about'
        new_slug = set_unique_top_level_url(test_slug)
        self.assertEqual(new_slug, 'about-1')


class TestUniqueSuiteURLs(TestCase):
    def setUp(self):
        from suites.models import Suite
        User = get_user_model()
        self.user = User.objects.create_user('test@test.com', 'foobar')
        self.user.slug = 'tester-testerson'
        self.user.save()

        self.user2 = User.objects.create_user('test2@test.com', 'foobar')

        self.suite = Suite.objects.create(owner=self.user, name='Test-Suite', slug='test-suite')

    def tearDown(self):
        del self.user
        del self.user2
        del self.suite

    def test_unique_no_match(self):
        test_slug = 'no-match'
        new_slug = set_unique_suite_url(self.user, test_slug)
        self.assertEqual(test_slug, new_slug)

    def test_matches_suite(self):
        test_slug = 'test-suite'
        new_slug = set_unique_suite_url(self.user, test_slug)
        self.assertEqual(new_slug, 'test-suite-1')

    def test_non_match_other_owner_suite(self):
        test_slug = 'test-suite'
        new_slug = set_unique_suite_url(self.user2, test_slug)
        self.assertEqual(new_slug, 'test-suite')







