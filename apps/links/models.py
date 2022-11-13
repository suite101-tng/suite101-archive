from __future__ import division
import time, re
from urllib.parse import urlparse
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db.models.signals import post_save
from model_utils import Choices
from model_utils.models import TimeStampedModel
from suites.models import SuitePost
from notifications.models import Notification
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.template.defaultfilters import wordcount
from django.template.defaultfilters import slugify
from lib.utils import generate_hashed_id, get_serialized_list, diff
from lib.cache import invalidate_object
from django.utils.html import strip_tags
from lib.enums import *
from .utils import process_provider_image
import json

class LinkManager(models.Manager):
    def published(self):
        return super(LinkManager, self).all().filter(status=Link.STATUS.published)

class Link(TimeStampedModel):
    link = models.URLField(max_length=512,blank=True,default='')
    provider = models.ForeignKey('links.LinkProvider', related_name='provider_links', null=True, blank=True, on_delete=models.SET_NULL)
    hashed_id = models.CharField(blank=True, max_length=50, db_index=True)
    tag_list = models.TextField(blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='links', db_index=True, null=True, blank=True, on_delete=models.SET_NULL)
    oembed_string = models.TextField(blank=True)

    STATUS = Choices('draft', 'published', 'deleted')
    status = models.CharField(choices=STATUS, default=STATUS.published,
                              max_length=20, db_index=True)

    MEDIA_TYPE = Choices('general', 'media', 'photo', 'tweet', 'instagram', 'unknown')
    media_type = models.CharField(choices=MEDIA_TYPE, default=MEDIA_TYPE.unknown,
                              max_length=20, db_index=True)
    notification_object = GenericRelation(Notification)    
    suite_post = GenericRelation(SuitePost, related_query_name='post')

    objects = LinkManager()

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        ''' override save to ensure links always have a LinkProvider object '''
        if not self.provider:
            if self.oembed_string:
                oembed_string = json.loads(self.oembed_string)
                try:
                    provider_url = oembed_string['provider_url']
                except Exception as e:
                    try:
                        provider_url = slug.rsplit('/',1)[0]
                    except Exception as e:
                        provider_url = ''

                try:
                    provider_name = oembed_string['provider_name']
                except Exception as e:
                    provider_name = ''

                provider, created = LinkProvider.objects.get_or_create(link=self)
                provider.name = provider_name
                provider.link = provider_url
                try:
                    provider.image = process_provider_image(provider, json.loads(self.oembed_string))
                except Exception as e:
                    print('failed to get provider image: %s' % e)

                provider.save()
                self.provider = provider

        return super(Link, self).save(*args, **kwargs)

    def invalidate(self):
        invalidate_object(self)
    
    def get_media_url(self):
        try:
            oembed_string = json.loads(self.oembed_string)
            return oembed_string['media']['url']
        except Exception as e:
            print('problem getting media url form link model: %s' % e)
            return None

    def get_link_json(self, request, attr=None):
        import json
        from links.sets import LinkTeaser
        from lib.utils import get_serialized_list
        if not attr:           
            return get_serialized_list(request, [self.pk],"link:mini")
        else:
            teaser_json = get_serialized_list([self.pk],"link:mini")[0]
            try:
                return teaser_json[attr]
            except Exception as e:
                print(e)

    def get_hashed_id(self):
        NO_OWNER = 123456789 # Dummy value for the encoder
        if not self.hashed_id:
            self.hashed_id = generate_hashed_id(NO_OWNER, HASH_TYPE_LINK, self.pk)
            self.save()
        return self.hashed_id

    def get_heading(self):
        oembed_string = json.loads(self.oembed_string)
        heading = ''
        try:
            heading = oembed_string['title']
        except Exception as e:
            pass

        if not heading:
            try:
                heading = embed['description']
            except:
                pass

        heading = 'Untitled link from %s' % self.provider.name if not heading else heading
        return heading

    def build_search_text(self):
        string = ''
        embed = json.loads(self.oembed_string)
        try:
            title = str(embed['title'])
        except:
            title = str('');
        try:
            description = str(embed['description'])
        except:
            description = str('');
        try:
            provider_name = str(self.provider.name)
        except Exception as e:
            provider_name = str('');
        string = title + '\n' + description + '\n' + provider_name 
        return string

    def get_absolute_url(self):
        return reverse('link_detail', kwargs={'hashed_id': self.get_hashed_id()})
 
    def get_suite_names(self):
        from lib.cache import get_object_from_pk
        from suites.models import Suite
        names = []
        suite_pks = self.get_suite_pks(None, True)
        if not suite_pks:
            return None
        for suite_pk in suite_pks:
            suite = get_object_from_pk(Suite, suite_pk, False)
            name = suite.name.encode('ascii', 'ignore').decode('ascii')
            if not name in names:
                names.append(name)
        return names

    def get_suite_pks(self, request=None, fetch_all=False):
        suite_pks = []
        if fetch_all:
            suite_pks = SuitePost.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk).values_list('suite__pk', flat=True)
        else:
            if not request.user.is_authenticated():
                suite_pks = SuitePost.objects.filter(suite__private=False, content_type=ContentType.objects.get_for_model(self), object_id=self.pk).values_list('suite__pk', flat=True)
            else:
                suite_posts = SuitePost.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk).select_related('suite')
                suite_pks = [sp.suite.pk for sp in suite_posts if not sp.suite.private or request.user.member_of(sp.suite)]
        
        # do we need to dedupe this list?
        # for pk in suite_pks:
        #     if not pk in suite_pks:
        #         suite_pks.append(pk)
        return suite_pks

    def get_suites(self, request):
        suite_pks = self.get_suite_pks(request)
        if not suite_pks:
            return None
        return get_serialized_list(request, suite_pks,'suite')

    def get_response_pks(self):
        from articles.models import StoryParent
        return StoryParent.objects.all().filter(object_id=self.pk, story__status='published').values_list('story__pk', flat=True).order_by('-story__created')

    def get_published_children(self, request):
        response_pks = self.get_response_pks()
        if response_pks:
            try:
                responses = get_serialized_list(request, response_pks,'story:mini')
                auths = []
                for resp in responses:
                    if not resp['author']['id'] in auths:
                        auths.append(resp['author']['id'])
                response_auths = json.dumps(get_serialized_list(request, auths,'user:mini')[:3])
            except Exception as e:
                print('failed to get responses and resp_auths: %s' % e)

        return responses, response_auths
            
class LinkProviderImage(TimeStampedModel):
    image = models.ImageField(upload_to='link_providers/image')
    provider = models.ForeignKey('links.LinkProvider', related_name='provider_images', blank=True, null=True)

    def provider_image_filename(instance, filename=None):
        import uuid
        return 'link_providers/image/%s.png' % uuid.uuid4()

    def get_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image.url) if self.image else ''
        else:
            return self.image.url if self.image else ''      

class LinkProvider(models.Model):
    link = models.URLField(max_length=512,blank=True,default='')
    name = models.CharField(max_length=255, blank=True, db_index=True)  
    # icon = models.ImageField(upload_to='link_providers/icon', blank=True, null=True)
    image = models.ForeignKey('links.LinkProviderImage', blank=True, null=True, related_name='provider_image')
    STATUS = Choices('ok', 'banned', 'unknown')
    status = models.CharField(choices=STATUS, default=STATUS.unknown,
                              max_length=20, db_index=True) 

    @property
    def banned(self):
        return self.is_banned()

    def is_banned(self):
        return True if self.status=='banned' else False

    def invalidate(self):
        invalidate_object(self)