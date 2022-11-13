from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from lib.tests import Suite101BaseTestCase
from articles.models import Article

from suites.models import *

class TestSuitesModels(Suite101BaseTestCase):
    def setUp(self):
        User = get_user_model()
        super(TestSuitesModels, self).setUp()
        self.suite = Suite.objects.create(
            name='test suite',
            owner=self.user
        )
        SuiteMember.objects.create(suite=self.suite, user=self.user)
        self.user2 = User.objects.create_user('test2@test.com', 'foobar')
        self.user2.is_active = True
        self.user2.save()

    def tearDown(self):
        del self.suite

    def test_unicode(self):
        self.assertEqual(self.suite.__unicode__(), 'test suite')

    def test_absolute_url(self):
        self.assertEqual(self.suite.get_absolute_url(), '/s/%s' % self.suite.get_hashed_id())

    def test_blank_name(self):
        suite2 = Suite()
        suite2.name = '   '
        suite2.owner = self.user
        suite2.save()
        self.assertEqual(suite2.slug, 'suite')
