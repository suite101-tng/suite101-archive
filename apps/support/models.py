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
import json

class SupportQuestion(TimeStampedModel):
    featured = models.DateTimeField(null=True, db_index=True)
    title = models.CharField(max_length=255, blank=True)
    answer = models.TextField()
    published = models.BooleanField(default=False)
    tag_list = models.TextField(blank=True)
    category = models.ForeignKey('support.SupportCategory', related_name='category_questions', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created']

    def invalidate(self):
        invalidate_object(self)
    
class SupportCategory(TimeStampedModel):
    name = models.TextField()
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created']

    def invalidate(self):
        invalidate_object(self)