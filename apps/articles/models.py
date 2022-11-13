from __future__ import division
import time
import re

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import wordcount, truncatechars, slugify
from django.utils.html import strip_tags
from articles.templatetags.bleach_filter import bleach_filter
import json
from django.http import HttpRequest
from lib.cache import invalidate_object
from autoslug import AutoSlugField
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from model_utils import Choices
from model_utils.fields import SplitField
from lib.enums import *
from notifications.models import Notification
from links.models import Link
from lib.utils import delete_all_images, generate_hashed_id, get_serialized_list, diff, api_serialize_resource_obj
from suites.models import Suite, SuitePost
User = settings.AUTH_USER_MODEL
class ArticleManager(models.Manager):
    def published(self):
        return super(ArticleManager, self).all().filter(status=Article.STATUS.published)

    def archived(self):
        return super(ArticleManager, self).all().filter(status=Article.STATUS.published, archive=True)

    def drafts(self):
        return super(ArticleManager, self).all().filter(status=Article.STATUS.draft)

class Article(models.Model):
    """
    Article model
    """
    author = models.ForeignKey(User,
                               related_name='articles', db_index=True)

    # taken from TimeStampedModel, but adding a db_index to the created field
    created = AutoCreatedField(db_index=True, editable=True)
    modified = AutoLastModifiedField()
    
    saved_on = models.DateTimeField(null=True, db_index=True)
    slug = AutoSlugField(max_length=100, populate_from='get_slug', unique=True, db_index=True, editable=True)
    
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.TextField(blank=True)
    body = SplitField(blank=True)
    body_length = models.IntegerField(null=True)
    word_count = models.IntegerField(default=0)

    story_dup = models.BooleanField(default=False)
    external_canonical = models.URLField('Canonical', blank=True)

    # response from AlchemyAPI fetch on save/create:
    alchemy_entity_str = models.TextField(blank=True)
    alchemy_keyword_str = models.TextField(blank=True)    
    # extracted from AlchemyAPI objects above
    entity_list = models.TextField(blank=True)
    keyword_list = models.TextField(blank=True)
    # user-entered tags
    tag_list = models.TextField(blank=True)

    STATUS = Choices('draft', 'published', 'deleted')
    status = models.CharField(choices=STATUS, default=STATUS.draft,
                              max_length=20, db_index=True)

    ADS_OVERRIDE = Choices('auto', 'show', 'hide')
    ads_override = models.CharField(choices=ADS_OVERRIDE, default=ADS_OVERRIDE.auto,
                              max_length=20)

    featured = models.DateTimeField(null=True, db_index=True)
    hashed_id = models.CharField(blank=True, max_length=50, db_index=True)
    
    deferred = models.BooleanField(default=False)
    archive = models.BooleanField(default=False, db_index=True)
    
    notification_object = GenericRelation(Notification)    
    suite_post = GenericRelation(SuitePost, related_query_name='post')

    objects = ArticleManager()

    class Meta:
        verbose_name_plural = "Articles"
        ordering = ['-created']

    class CacheKey:
        obj_cache_key = 'story:obj'

    def get_slug(self):
        return self.title if self.title else 'untitled'

    def __unicode__(self):
        return '%s (%s)' % (self.title, self.pk)

    def get_absolute_url(self):
        return reverse('story_detail', kwargs={'author': self.author.slug, 'hashed_id': self.get_hashed_id()})

    def save(self, *args, **kwargs):
        self.title = self.title.strip()
        return super(Article, self).save(*args, **kwargs)

    @property
    def parent_obj(self):
        return self.get_parent_object()

    @property
    def published(self):
        return self.status == self.STATUS.published

    @property
    def draft(self):
        return self.status == self.STATUS.draft

    @property
    def deleted(self):
        return self.status == self.STATUS.deleted

    def get_heading(self):
        title = self.title
        if not title:
            title = strip_tags(truncatechars(bleach_filter(self.body.excerpt, ['p']), 60))
        return title

    def get_hashed_id(self):
        if not self.hashed_id:
            self.hashed_id = generate_hashed_id(self.author.pk, HASH_TYPE_STORY, self.pk)
            self.save()
        return self.hashed_id
                 
    def invalidate(self):
        ''' invalidate story, parent, user, associated suites '''
        invalidate_object(self)
        self.author.save()
        self.author.invalidate()

    def mark_deleted(self):
        from articles.tasks import purge_deleted_story
        author = self.author
        self.invalidate()
        self.status = self.STATUS.deleted
        self.save()
        author.reset_last_published_date()
        purge_deleted_story(self)
        # return super(Article, self).delete()

def article_images_file_name(instance, filename=None):
    import uuid
    return 'article_images/orig/%s.jpg' % uuid.uuid4()

class StoryEmbed(TimeStampedModel):
    ''' Can be any object (eg link, image, story) '''
    ''' Caption, credits pertain to the instance of the reusable embed object '''
    story = models.ForeignKey(Article, related_name='embeds', null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')    

    caption = models.CharField(max_length=512, blank=True)
    cover = models.BooleanField(default=False)
    spill = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.cover:
            other_covers = StoryEmbed.objects.filter(story=self.story, cover=True).exclude(pk=self.pk)
            if other_covers:
                for embed in other_covers:
                    embed.cover = False
                    embed.save()
        self.invalidate()
        self.content_object.invalidate()

        super(StoryEmbed, self).save(*args, **kwargs) 

    def invalidate(self):
        invalidate_object(self)        

class StoryParent(models.Model):
    story = models.OneToOneField(Article, related_name='story_parent')
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    notification_object = GenericRelation(Notification)    

    def invalidate(self):
        invalidate_object(self)        

class ArticleImage(models.Model):
    image = models.ImageField(upload_to=article_images_file_name, blank=True, null=True)
    image_large = models.ImageField(upload_to='article_images/large', blank=True, null=True)
    image_small = models.ImageField(upload_to='article_images/small', blank=True, null=True)
    article = models.ForeignKey(Article, related_name='images', null=True, blank=True)
    is_main_image = models.BooleanField(default=False)

    upload_url = models.URLField(null=True, blank=True)

    IMAGE_TYPE = Choices('normal', 'lefty', 'righty')
    image_type = models.CharField(choices=IMAGE_TYPE, default=IMAGE_TYPE.normal, max_length=10)
    landscape = models.BooleanField(default=True)

    caption = models.CharField(max_length=512, blank=True)
    credit = models.CharField(max_length=512, blank=True)
    credit_link = models.CharField(max_length=512, blank=True)
    sort_order = models.IntegerField(default=0)

    legacy_image_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['sort_order']

    def save(self, *args, **kwargs):
        if self.upload_url and not self.image:
            from django.core.files.base import ContentFile
            from lib.utils import download_image_from_url, valid_img
            import cStringIO
            image = download_image_from_url(self.upload_url)
            if image:
                try:
                    filename = article_images_file_name(self)
                    self.image = filename
                    tempfile = image
                    tempfile_io = cStringIO.StringIO() # Will make a file-like object in memory that you can then save
                    tempfile.save(tempfile_io, format=image.format)
                    self.image.save(filename, ContentFile(tempfile_io.getvalue()), save=False) # Set save=False otherwise you will have a looping save method
                    self.upload_url = ''
                except Exception as e:
                    print ("Error trying to save model: saving image failed: " + str(e))
                    pass
        super(ArticleImage, self).save(*args, **kwargs) 

    def get_orig_image_url(self):
        if 'localhost' in settings.SITE_URL:
            # return "%s%s" % (settings.SITE_URL, self.image.url) if self.image else ''
            return "%s%s" % ('https://static.suite.io', self.image.url.replace('media/', '')) if self.image else ''
        else:
            return self.image.url if self.image else ''

    def get_large_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image_large.url) if self.image_large else ''
        else:
            return self.image_large.url if self.image_large else ''

    def get_small_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image_small.url) if self.image_small else ''
        else:
            return self.image_small.url if self.image_small else ''

    def invalidate(self):
        invalidate_object(self)  

    def delete(self, *args, **kwargs):
        delete_all_images(self)
        super(ArticleImage, self).delete(*args, **kwargs)