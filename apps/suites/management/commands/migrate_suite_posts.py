import time, datetime
from django.core.management.base import BaseCommand
from dateutil import parser

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from lib.utils import queryset_iterator
from articles.models import Article
from suites.models import Suite, SuiteStory, SuiteMember, SuitePost
from suites.tasks import refresh_suite_stats, process_new_suite_member
from lib.cache import get_object_from_pk
from lib.sets import RedisObject

class Command(BaseCommand):
    help = 'usage: python manage.py migrate_suite_posts'


    def handle(self, *args, **options):
        User = get_user_model()

        suite_stories = SuiteStory.objects.all()
        if suite_stories:
            for ss in suite_stories.iterator():
                try:
                    if ss.suite.owner.is_active and ss.story.author.is_active:
                        sp = SuitePost.objects.create(suite=ss.suite, added_by=ss.story.author, content_type=ContentType.objects.get_for_model(Article), object_id=ss.story.pk)
                        sp.created = ss.story.created
                        sp.save()
                except Exception as e:
                    print('problem creating suitePost object: %s' % e)
