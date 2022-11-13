import celery
import json
import string
import time

from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
from django.template.defaultfilters import wordcount
from django.conf import settings

from lib.tasks import send_email_alert
from suites.models import Suite, SuiteMember
from lib.enums import *
   
@celery.task(name='suites.tasks.refresh_suite_tags')
def refresh_suite_tags(story):
    from django.contrib.contenttypes.models import ContentType
    import json, collections
    from articles.models import Article
    from suites.models import Suite, SuitePost
    suites = []
    suite_posts = SuitePost.objects.filter(content_type=ContentType.objects.get_for_model(Article), object_id=story.pk).select_related('suite')
    if suite_posts:
        for post_obj in suite_posts:
            if not post_obj.suite in suites:
                suites.append(post_obj.suite)
        if suites:
            for suite in suites:
                all_tags = []
                suite_suite_posts = SuitePost.objects.filter(suite=suite, post__status="published").exclude(post__tag_list='' or [])
                for post_obj in suite_suite_posts:
                    try:
                        for tag in json.loads(str(post_obj.story.tag_list)):
                            all_tags.append(tag)
                    except:
                        pass
                collected_tags = collections.Counter(all_tags)
                suite.tag_list = json.dumps(([item for item,count in collected_tags.most_common(100)]))
                suite.save()

    else:
        pass

@celery.task(name='suites.tasks.refresh_suite_stats')
def refresh_suite_stats(suite):
    from django.contrib.contenttypes.models import ContentType
    from lib.models import Follow
    from lib.sets import RedisObject
    from stats.sets import UserStats, SuiteStats

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()

    try:
        story_count = int(suite.get_stories_count())
        redis.pipeline(SuiteStats(suite.pk).set(story_count, "stories"))            
        member_count = len(suite.get_member_pks())
        redis.pipeline(SuiteStats(suite.pk).set(member_count, "members"))            
        if member_count > 1:
            redis.pipeline(SuiteStats(suite.pk).set(member_count-3, "others"))            

        followers = Follow.objects.filter(content_type=ContentType.objects.get_for_model(suite), object_id=suite.pk).values_list('user_id', flat=True).count()
        redis.pipeline(SuiteStats(suite.pk).set(followers, "followers"))            

    except Exception as e:
        print(e)

    pipe.execute()

@celery.task(name='suites.tasks.refresh_suite_featured_members')
def refresh_suite_featured_members(suite):
    from .sets import SuiteFeaturedMembers
    SuiteFeaturedMembers(suite.pk).clear_set()    

@celery.task(name='suites.tasks.process_new_suite')
def process_new_suite(suite, fanout=True):
    from suites.models import Suite, SuiteMember
    # make sure the owner is also a member
    SuiteMember.objects.get_or_create(suite=suite, user=suite.owner, status='owner')

    # Add the owner to the Suite member set
    process_new_suite_member(suite, suite.owner)

    suite.invalidate()
    suite.owner.invalidate()

    if fanout:
        # fanout suite to owner's followers
        fanout_new_suite(suite)

@celery.task(name='suites.tasks.process_new_suite_member')
def process_new_suite_member(suite,member):
    refresh_suite_stats(suite)
    # TODO: fan out a notification to other suite members, followers

@celery.task(name='suites.tasks.fanout_new_suite')
def fanout_new_suite(suite):
    from dateutil import parser
    time_score = time.mktime(suite.created.timetuple())

@celery.task(name='suites.tasks.fanout_add_to_suite')
def fanout_add_to_suite(suite_story):
    suite_story.fanout_notification()

@celery.task(name='suites.tasks.fanout_suite_invite')
def fanout_suite_invite(suite_invite, suppress_email=False):
    suite_invite.fanout_notification()
    from suites.models import SuiteInvite
    from lib.tasks import send_email_alert, send_external_invite

    if suite_invite.email_invite and not suite_invite.user_invited:
        # Send out an intro-invite email
        send_external_invite(suite_invite)

    else:
        if not suppress_email:
            # Send out an email
            send_email_alert.delay(suite_invite.user_inviting, suite_invite.suite, suite_invite.user_invited)

@celery.task(name='suites.tasks.process_suite_editor')
def process_suite_editor(member):
    member.fanout_notification()
    suite.invalidate()

@celery.task(name='suites.tasks.fanout_new_suite_member')
def fanout_new_suite_member(suite_member): 
    suite_member.fanout_notification()
