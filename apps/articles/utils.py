import logging
import json
import base64
import datetime
import string
import redis
from django.template.defaultfilters import wordcount

from django.conf import settings

from articles.models import *
from lib.utils import suite_render, api_serialize_resource_obj
from lib.enums import ARTICLE_IMAGE_LARGE_WIDTH

logger = logging.getLogger(__name__)

def has_large_main_image(story_pk):
    images = ArticleImage.objects.filter(is_main_image=True, article__pk=story_pk)
    if not images:
        return False
    if images:                           
        for i in images:
            try:
                if i.image.width > ARTICLE_IMAGE_LARGE_WIDTH:
                    return True
            except Exception as e:
                continue
    return False

def render_teasers(request, articles, show_user=True, template='story-teaser'):
    from articles.api import StoryMiniResource
    from profiles.api import UserMiniResource
    articles_array = []
    # memoize the authors as we go.
    authors = {}

    for article in articles:
        article_obj = api_serialize_resource_obj(article, StoryMiniResource(), request)
        article_obj['showUser'] = show_user

        # if show user if true, we have to serialize the user object and stick it into the story mini
        if show_user:
            if not article.author.pk in authors:
                author = api_serialize_resource_obj(article.author, UserMiniResource(), request)
                authors[article.author.pk] = author
            else:
                author = authors[article.author.pk]
            article_obj['author'] = author

        articles_array.append(article_obj)
    return suite_render(request, template, articles_array, multiple=True)

''' api related '''
def _post_article_publish(story):
    from articles.tasks import post_publish
    story.status = story.STATUS.published
    story.created = datetime.datetime.now()
    story.get_hashed_id()
    story.save()
    story.invalidate
    post_publish.delay(story)