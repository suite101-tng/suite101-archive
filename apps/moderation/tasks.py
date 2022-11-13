import celery
import json
import string
import time
import datetime

from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
from django.template.defaultfilters import wordcount
from django.conf import settings

from lib.tasks import send_email_alert
from articles.models import Article
from suites.models import Suite
from articles.sets import RecommendedStoriesSet
from lib.enums import *

@celery.task(name='moderation.tasks.add_featured_member')
def add_featured_member(user):
    from profiles.sets import FeaturedMemberSet
    FeaturedMemberSet().add_to_set(user.pk)

@celery.task(name='moderation.tasks.remove_featured_member')
def remove_featured_member(user):
    from profiles.sets import FeaturedMemberSet
    FeaturedMemberSet().remove_from_set(user.pk)

def clear_featured(content_type):
    from lib.sets import RedisObject
    from articles.sets import LeadStoryPool, RecommendedStoriesSet
    from suites.sets import FeaturedSuiteSet
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    if content_type == 'story':
        redis.pipeline(RecommendedStoriesSet().clear_set())
        redis.pipeline(LeadStoryPool().clear_set())
        pipe.execute()
    
    elif content_type == 'suite':
        FeaturedSuiteSet().clear_set()
