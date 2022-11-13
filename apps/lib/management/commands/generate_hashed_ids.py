from django.core.management.base import BaseCommand

from articles.models import Article
from suites.models import Suite

from lib.utils import queryset_iterator


class Command(BaseCommand):
    help = 'usage: python manage.py generate_hashed_ids'

    def handle(self, *args, **options):
        # Suite.objects.all().update(hashed_id='')
        for suite in queryset_iterator(Suite.objects.filter(hashed_id='')):
            suite.get_hashed_id()

        # Article.objects.all().update(hashed_id='')
        for article in queryset_iterator(Article.objects.filter(hashed_id='')):
            article.get_hashed_id()
