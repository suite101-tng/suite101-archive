from django.contrib.syndication.views import Feed
from django.utils import feedgenerator
from django.contrib.auth import get_user_model

from lib.cache import get_object_from_pk
from lib.cache import get_object_from_slug
from articles.sets import RecommendedStoriesSet
from suites.models import Suite

FEED_PAGE_SIZE = 30

class RSSLatestArticleFeed(Feed):
    title = 'Recommended stories'
    link = '/rss/recommended'
    description = 'Latest stories from all around Suite'
    feed_type = feedgenerator.Rss201rev2Feed

    def items(self):
        return RecommendedStoriesSet().get_set()

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.subtitle


class RSSUserArticleFeed(Feed):
    def get_object(self, request, slug):
        User = get_user_model()
        return get_object_from_slug(User, slug)

    def title(self, obj):
        return "Latest stories by %s" % obj.get_full_name()

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return "Suite101 - Latest stories posted by %s" % obj.get_full_name()

    def items(self, obj):
        return obj.articles.published()[:FEED_PAGE_SIZE]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.subtitle
