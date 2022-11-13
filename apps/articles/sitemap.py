from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse
from .models import Article
from lib.enums import STORY_LENGTH_INDEX_THRESHOLD

class ArticleSitemap(Sitemap):
    limit = 10000
    changefreq = "daily"
    priority = 0.25
    protocol = 'https'

    def items(self):
        return Article.objects.published() \
                    .values('author__slug', 'saved_on', 'hashed_id') \
                    .filter(author__approved=True, author__is_active=True, word_count__gte=STORY_LENGTH_INDEX_THRESHOLD).order_by('-created')

    def location(self, obj):
        return reverse('story_detail', kwargs={'author': obj['author__slug'], 'hashed_id': obj['hashed_id']})

    def lastmod(self, obj):
        return obj['saved_on']
