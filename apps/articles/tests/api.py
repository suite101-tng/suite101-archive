from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django_nose.tools import *
from django.core import mail

from lib.tests import Suite101ResourceBaseTestCase
from lib.models import Follow
from suites.models import Suite
from articles.models import Article, ArticleImage, ArticleRecommend

@override_settings(CELERY_ALWAYS_EAGER=True)
class StoryResourceTest(Suite101ResourceBaseTestCase):
    def setUp(self):
        super(StoryResourceTest, self).setUp()
        self.stories = []

        self.stories.append(
            Article.objects.create(
                author=self.user,
                slug='some-slug-%s-that-is-unique' % 0,
                title='Yup',
                body='Yes',
                status='published',
            )
        )
        self.stories[0].save()

        for i in range(4):
            index = i + 1
            self.stories.append(
                Article.objects.create(
                    author=self.user,
                    slug='some-slug-%s-that-is-unique' % index,
                    title='Yup',
                    body='Yes',
                    status='published',
                )
            )

        self.story1 = self.stories[0]
        self.detail_url = '/api/v1/story/{0}/'.format(self.story1.pk)
        self.post_data = {
            'title': 'new title',
            'subtitle': 'new subtitle',
            'body': 'this is my new article',
            'publish': True,
        }

        self.suite1 = Suite.objects.create(
                        name='Test Suite 1',
                        owner=self.user
                    )
        self.suite2 = Suite.objects.create(
                        name='Test Suite 2',
                        owner=self.user
                    )

    def tearDown(self):
        del self.story1
        del self.detail_url
        del self.post_data
        del self.suite1
        del self.suite2

    def test_get_list_json(self):
        resp = self.api_client.get('/api/v1/story/', format='json')
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 5)
        # Here, we're checking an entire structure for the expected data.
        # import pdb; pdb.set_trace()
        new_obj = self.deserialize(resp)['objects'][4]
        self.assertEqual(new_obj['id'], self.story1.pk)
        self.assertEqual(new_obj['author']['resourceUri'], '/api/v1/user_mini/{0}/'.format(self.story1.author.slug))
        self.assertEqual(new_obj['author']['id'], self.story1.author.pk)
        self.assertEqual(new_obj['title'], 'Yup')
        self.assertEqual(new_obj['resourceUri'], '/api/v1/story/{0}/'.format(self.story1.pk))

    def test_get_list_unauthenticated(self):
        self.api_client.client.logout()
        self.test_get_list_json()

    def test_get_detail_json(self):
        resp = self.api_client.get(self.detail_url, format='json')
        self.assertValidJSONResponse(resp)

        # spot check some data
        new_obj = self.deserialize(resp)
        self.assertEqual(new_obj['id'], self.story1.pk)
        self.assertEqual(new_obj['author']['resourceUri'], '/api/v1/user_mini/{0}/'.format(self.story1.author.slug))
        self.assertEqual(new_obj['author']['id'], self.story1.author.pk)
        self.assertEqual(new_obj['title'], 'Yup')
        self.assertEqual(new_obj['resourceUri'], '/api/v1/story/{0}/'.format(self.story1.pk))

    def test_get_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.test_get_detail_json()

    def test_post_list(self):
        self.assertEqual(Article.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))
        self.assertEqual(Article.objects.count(), 6)

        # newest should be first
        story = Article.objects.all()[0]
        story_resource_uri = '/api/v1/story/{0}/'.format(story.pk)
        resp = self.api_client.get(story_resource_uri, format='json')
        self.assertValidJSONResponse(resp)
        # spot check some data
        new_obj = self.deserialize(resp)
        self.assertEqual(new_obj['author']['id'], self.user.pk)

    def test_post_list_with_no_title(self):
        self.post_data['title'] = ''
        self.assertEqual(Article.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))
        self.assertEqual(Article.objects.count(), 6)

    def test_post_list_with_blank_title(self):
        self.post_data['title'] = '      '
        self.assertEqual(Article.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))
        self.assertEqual(Article.objects.count(), 6)

    def test_post_list_with_parent(self):
        story = Article.objects.all()[0]
        self.post_data['parent'] = '/api/v1/story/{0}/'.format(story.pk)
        self.assertEqual(Article.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))
        self.assertEqual(Article.objects.count(), 6)

        # newest should be first
        story = Article.objects.all()[0]
        story_resource_uri = '/api/v1/story/{0}/'.format(story.pk)
        resp = self.api_client.get(story_resource_uri, format='json')
        self.assertValidJSONResponse(resp)
        # spot check some data
        new_obj = self.deserialize(resp)
        self.assertEqual(new_obj['author']['id'], self.user.pk)        
        self.assertEquals(len(mail.outbox), 0)

    def test_post_list_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))

    def test_post_list_no_title(self):
        self.post_data['title'] = ''
        self.assertEqual(Article.objects.count(), 5)
        self.assertHttpCreated(self.api_client.post('/api/v1/story/', format='json', data=self.post_data))
        self.assertEqual(Article.objects.count(), 6)

    def test_put_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.put(self.detail_url, format='json', data={}))

    def test_put_detail(self):
        self.test_post_list()
        # newest should be first
        story = Article.objects.all()[0]
        story_resource_uri = '/api/v1/story/{0}/'.format(story.pk)

        # Grab the current data & modify it slightly.
        original_data = self.deserialize(self.api_client.get(story_resource_uri, format='json'))
        new_data = original_data.copy()
        new_data['title'] = 'Updated: First Post'
        new_data['body'] = 'New Body'

        self.assertEqual(Article.objects.count(), 6)
        self.assertHttpOK(self.api_client.put(story_resource_uri, format='json', data=new_data))
        # Make sure the count hasn't changed & we did an update.
        self.assertEqual(Article.objects.count(), 6)
        # Check for updated data.
        self.assertEqual(Article.objects.get(pk=story.pk).title, 'Updated: First Post')
        self.assertEqual(Article.objects.get(pk=story.pk).body.content, 'New Body')

    def test_delete_detail_unauthenticated(self):
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.delete(self.detail_url, format='json'))

    def test_delete_detail(self):
        self.assertEqual(Article.objects.count(), 5)
        # import pdb; pdb.set_trace()
        self.assertHttpAccepted(self.api_client.delete(self.detail_url, format='json'))
        self.assertEqual(Article.objects.count(), 5)
        self.assertEqual(Article.objects.published().count(), 4)

    def test_put_detail_as_mod(self):
        self.test_post_list()
        self.login_moderator()
        # newest should be first
        story = Article.objects.all()[0]
        story_resource_uri = '/api/v1/story/{0}/'.format(story.pk)

        # Grab the current data & modify it slightly.
        original_data = self.deserialize(self.api_client.get(story_resource_uri, format='json'))
        new_data = original_data.copy()
        new_data['title'] = 'Updated: Moderator Edit'

        self.assertEqual(Article.objects.count(), 6)
        self.assertHttpOK(self.api_client.put(story_resource_uri, format='json', data=new_data))
        # Make sure the count hasn't changed & we did an update.
        self.assertEqual(Article.objects.count(), 6)
        # Check for updated data.
        self.assertEqual(Article.objects.get(pk=story.pk).title, 'Updated: Moderator Edit')
        # make sure the author is still the author
        self.assertEqual(Article.objects.get(pk=story.pk).author, self.user)


class StoryImageResourceTest(Suite101ResourceBaseTestCase):
    def setUp(self):
        super(StoryImageResourceTest, self).setUp()
        self.story = Article.objects.create(
                        author=self.user,
                        slug='some-slug-that-is-unique',
                        title='Yup',
                        body='Yes',
                        status='published',
                    )
        self.story.save()

    def tearDown(self):
        del self.story

    def upload_via_CBV(self):
        import os
        from django.core.urlresolvers import reverse
        from django.core.files import File
        DIRNAME = os.path.abspath(os.path.dirname(__file__))

        url = reverse('story_image_upload')
        data = {
            'image': File(open(os.path.join(DIRNAME, '../../../static/images/temp_default_user.jpg'))),
        }
        response = self.api_client.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert_ok(response)
        self.assertEqual(ArticleImage.objects.count(), 1)
        return ArticleImage.objects.all()[0].pk

    def test_put_detail(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)

        # Grab the current data & modify it slightly.
        original_data = self.deserialize(self.api_client.get(image_resource_uri, format='json'))
        new_data = original_data.copy()
        new_data['caption'] = 'Updated: Caption'
        new_data['isMainImage'] = True

        self.assertEqual(ArticleImage.objects.count(), 1)
        self.assertHttpOK(self.api_client.put(image_resource_uri, format='json', data=new_data))
        # Make sure the count hasn't changed & we did an update.
        self.assertEqual(ArticleImage.objects.count(), 1)
        # Check for updated data.
        self.assertEqual(ArticleImage.objects.get(pk=image_id).caption, 'Updated: Caption')
        self.assertTrue(ArticleImage.objects.get(pk=image_id).is_main_image)

    def test_put_detail_empty(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)
        self.assertHttpOK(self.api_client.put(image_resource_uri, format='json', data={}))

    def test_put_detail_unauthenticated(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.put(image_resource_uri, format='json', data={}))

    def test_delete_detail_unauthenticated(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.delete(image_resource_uri, format='json'))

    def test_delete_detail_no_article(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)
        self.assertHttpAccepted(self.api_client.delete(image_resource_uri, format='json'))

    def test_add_image_to_article(self):
        image_id = self.upload_via_CBV()
        image_resource_uri = '/api/v1/story_image/{0}/'.format(image_id)
        story = Article.objects.all()[0]

        original_data = self.deserialize(self.api_client.get(image_resource_uri, format='json'))
        new_data = original_data.copy()
        new_data['story'] = {'pk': story.pk}
        self.assertEqual(ArticleImage.objects.count(), 1)
        self.assertHttpOK(self.api_client.put(image_resource_uri, format='json', data=new_data))
        self.assertEqual(ArticleImage.objects.count(), 1)

        self.assertEqual(Article.objects.get(pk=story.pk).images.all()[0].pk, image_id)
        self.assertEqual(Article.objects.get(pk=story.pk).images.count(), 1)

