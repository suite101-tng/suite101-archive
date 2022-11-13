from django.contrib.auth import get_user_model
from django_nose.tools import *

from lib.tests import Suite101ResourceBaseTestCase
from suites.models import Suite, SuiteImage, SuitePost, SuiteInvite, SuiteRequest, SuiteMember
from articles.models import Article

class SuiteResourceTest(Suite101ResourceBaseTestCase):
    def setUp(self):
        super(SuiteResourceTest, self).setUp()
        self.suites = []
        for i in range(5):
            self.suites.append(
                Suite.objects.create(
                    owner=self.user,
                    name='Test Suite %s' % i
                )
            )
        self.suite1 = self.suites[0]
        self.resource_uri = '/api/v1/suite/'
        self.detail_url = '/api/v1/suite/{0}/'.format(self.suite1.pk)
        self.post_data = {
            'name': 'test suite 3',
            'about': 'new about',
            'description': 'my new suite.',
        }

    def tearDown(self):
        del self.suites
        del self.suite1
        del self.resource_uri
        del self.detail_url
        del self.post_data

    def test_get_list_json(self):
        resp = self.api_client.get(self.resource_uri, format='json')
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 5)
        # Here, we're checking an entire structure for the expected data.
        # import pdb; pdb.set_trace()
        new_obj = self.deserialize(resp)['objects'][4]
        self.assertEqual(new_obj['id'], self.suite1.pk)
        self.assertEqual(new_obj['owner']['resourceUri'], '/api/v1/user_mini/{0}/'.format(self.suite1.owner.slug))
        self.assertEqual(new_obj['owner']['id'], self.suite1.owner.pk)
        self.assertEqual(new_obj['name'], 'Test Suite 0')
        self.assertEqual(new_obj['resourceUri'], '/api/v1/suite/{0}/'.format(self.suite1.pk))

    def test_get_list_unauthenticated(self):
        self.api_client.client.logout()
        self.test_get_list_json()

    def test_get_detail_json(self):
        resp = self.api_client.get(self.detail_url, format='json')
        self.assertValidJSONResponse(resp)

        # spot check some data
        new_obj = self.deserialize(resp)
        self.assertEqual(new_obj['id'], self.suite1.pk)
        self.assertEqual(new_obj['owner']['resourceUri'], '/api/v1/user_mini/{0}/'.format(self.suite1.owner.slug))
        self.assertEqual(new_obj['owner']['id'], self.suite1.owner.pk)
        self.assertEqual(new_obj['name'], 'Test Suite 0')
        self.assertEqual(new_obj['resourceUri'], '/api/v1/suite/{0}/'.format(self.suite1.pk))

    def test_get_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.test_get_detail_json()

    def test_post_list(self):
        self.assertEqual(Suite.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post(self.resource_uri, format='json', data=self.post_data))
        self.assertEqual(Suite.objects.count(), 6)

        # newest should be first
        suite = Suite.objects.all()[0]
        suite_resource_uri = '/api/v1/suite/{0}/'.format(suite.pk)
        resp = self.api_client.get(suite_resource_uri, format='json')
        self.assertValidJSONResponse(resp)
        # spot check some data
        new_obj = self.deserialize(resp)
        self.assertEqual(new_obj['owner']['id'], self.user.pk)
        self.assertEqual(new_obj['slug'], 'test-suite-3-1')

    def test_post_list_no_name(self):
        self.post_data['name'] = ''
        self.assertEqual(Suite.objects.count(), 5)
        self.assertHttpBadRequest(self.api_client.post(self.resource_uri, format='json', data=self.post_data))
        self.assertEqual(Suite.objects.count(), 5)

    def test_post_list_blank_name(self):
        self.post_data['name'] = '   '
        self.assertEqual(Suite.objects.count(), 5)
        self.assertHttpBadRequest(self.api_client.post(self.resource_uri, format='json', data=self.post_data))
        self.assertEqual(Suite.objects.count(), 5)

    def _add_suite_image(self):
        import os
        from django.core.files import File
        DIRNAME = os.path.abspath(os.path.dirname(__file__))
        return SuiteImage.objects.create(user=self.user,
            image=File(open(os.path.join(DIRNAME, '../../../static/images/temp_default_user.jpg')))
        )

    def test_post_list_with_image(self):
        suite_image = self._add_suite_image()
        self.post_data['hero_image'] = '/api/v1/suite_image/{0}/'.format(suite_image.pk)
        # self.post_data['hero_image'] = {
        #     'type': 'suite',
        #     'pk': suite_image.pk
        # }
        self.test_post_list()
        suite = Suite.objects.all()[0]
        self.assertEqual(suite_image, suite.hero_image)

    def test_post_list_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.post(self.resource_uri, format='json', data=self.post_data))

    def test_post_list_no_name(self):
        self.post_data['name'] = ''
        self.assertEqual(Suite.objects.count(), 5)
        self.assertHttpBadRequest(self.api_client.post(self.resource_uri, format='json', data=self.post_data))
        self.assertEqual(Suite.objects.count(), 5)

    def test_put_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.put(self.detail_url, format='json', data={}))

    def test_put_detail(self):
        self.test_post_list()
        # newest should be first
        suite = Suite.objects.all()[0]
        suite_resource_uri = '/api/v1/suite/{0}/'.format(suite.pk)

        # Grab the current data & modify it slightly.
        original_data = self.deserialize(self.api_client.get(suite_resource_uri, format='json'))
        new_data = original_data.copy()
        new_data['name'] = 'Updated: First Post'
        new_data['about'] = 'New About'
        new_data['newSlug'] = 'my-new-slug'

        self.assertEqual(Suite.objects.count(), 6)
        self.assertHttpOK(self.api_client.put(suite_resource_uri, format='json', data=new_data))
        # Make sure the count hasn't changed & we did an update.
        self.assertEqual(Suite.objects.count(), 6)

    def test_delete_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.delete(self.detail_url, format='json'))

class SuiteRequestResourceTest(Suite101ResourceBaseTestCase):
    def setUp(self):
        User = get_user_model()
        super(SuiteRequestResourceTest, self).setUp()
        self.suite = Suite.objects.create(
                        owner=self.user,
                        name='Test Suite',
                    )
    
        self.resource_uri = '/api/v1/suite_request/'

        self.user2 = User.objects.create_user('test2@test.com', 'foobar')
        self.user2.activate_user()
        self.user2.save()

    def tearDown(self):
        del self.suite
        del self.user2

