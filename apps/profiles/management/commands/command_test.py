from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from profiles.models import SuiteUser
from django.contrib.contenttypes.models import ContentType
import datetime
from lib.utils import queryset_iterator
from lib.cache import get_object_from_pk
from articles.models import *
from suites.models import *
from lib.enums import *

class Command(BaseCommand):
    help = 'usage: python manage.py command_test'

    def handle(self, *args, **options):

        # from django.http import Http404
        # import time
        # # from datetime import datetime, timedelta
        # import datetime
        # from lib.utils import queryset_iterator
        # from dateutil import parser
        # from lib.sets import RedisObject
        # from django.contrib.auth import get_user_model
        # from django.db.models import Sum, Count
        # from articles.models import Article
        # User = get_user_model()
        # start_time = time.time() # start stopwatch

        from articles.models import *
        stories = Article.objects.filter(author__pk=7444)
        for story in stories:
            images = story.images.all()
            if images:
                for image in images:
                    embed = StoryEmbed.objects.create(story=story, object_id=image.pk, content_type=ContentType.objects.get_for_model(ArticleImage))




        # from lib.sets import RedisObject
        # from articles.sets import UserMainStoryFeed
        # redis = RedisObject().get_redis_connection(slave=False)
        # pipe = redis.pipeline()  

        # # fill up all user's feeds      
        # from articles.tasks import fanout_new_story
        # epoch = datetime.datetime.now() - datetime.timedelta(days=300)

        # # users = queryset_iterator(User.objects.all())
        # stories = queryset_iterator(Article.objects.published().exclude(author__pk=7444).filter(created__gte=epoch))
        # for story in stories:
        #     print 'story %s' % story.pk
        #     fanout_new_story(story)


        # def rebuild_feed(user):
        #     your_stories = Article.objects.published().filter(author=user, created__gte=epoch).values_list('pk', flat=True)
        #     for story in your_stories:
        #         redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(story.pk, time_score)) 



        # for user in users:
        #     get followed people
        #     get followed suites
        #     get responses to you
        #     get your posts

        #     your_stories = Article.objects.published().filter(author=user, created__gte=epoch).values_list('pk', flat=True)
        #     for story in your_stories:
        #         redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(story.pk, time_score)) 

        # i = 0
        # for story in stories:
        #     tags_loaded = json.loads(str(story.tag_list))
        #     for tag in tags_loaded:
        #         redis.pipeline(TopTags(filter_type).increment(tag, 1))
        #         i += 1
        #     if i > 500:
        #         i = 0
        #         pipe.execute()
        # redis.pipeline(TopTags(filter_type).expire(tag_cache_lifespan))
        # pipe.execute()




        # '''Find users with short-short names'''
        # shortnames = User.objects.extra(where=["CHAR_LENGTH(first_name) < 3"]).filter(last_name='')
        # for user in shortnames:
        #     user.invalidate()
        #     user.delete()


        # from suites.models import Suite
        # suites = queryset_iterator(Suite.objects.all())
        # for suite in suites:
        #     if suite.featured:
        #         print 'featured %s on %s' % (suite.pk, suite.featured)
        #         suite.invalidate()