import celery
import logging
import time
import datetime
from django.contrib.auth import get_user_model

from lib.enums import *

@celery.task(name='profiles.tasks.refresh_user_tags')
def refresh_user_tags(user):
    import json, collections
    from articles.models import Article
    all_tags = []
    stories = Article.objects.published().filter(author=user).exclude(tag_list='' or [])
    for story in stories:
        try:
            for tag in json.loads(str(story.tag_list)):
                all_tags.append(tag)
        except:
            pass
    collected_tags=collections.Counter(all_tags)
    user.tag_list = json.dumps(([item for item,count in collected_tags.most_common(100)]))
    user.save()

@celery.task(name='profiles.tasks.trim_inactive_accounts')
def trim_inactive_accounts():
    from datetime import datetime, timedelta
    from django.contrib.auth import get_user_model
    from lib.utils import queryset_iterator
    from stats.sets import AdminDailyStatsTrimmedInactive
    User = get_user_model()
          
    time_limit = datetime.now() - timedelta(days=90)

    users = queryset_iterator(User.objects.all().filter(approved=False))
    i=0
    for user in users:
        if user.seen() < time_limit:
            user.is_active = False
            user.invalidate()
            user.save()
            i+=1
        
    if i:
        date_stamp = datetime.now().strftime("%Y-%m-%d")
        AdminDailyStatsTrimmedInactive().increment(i,date_stamp)

@celery.task(name='profiles.tasks.process_mutual_follow')
def process_mutual_follow(followed, following):
    from profiles.sets import MutualFollowsSet
    from lib.sets import RedisObject
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()
    if followed.is_following(following.pk, 'user'):
        redis.pipeline(MutualFollowsSet(following.pk).add_to_set(followed.pk))
        redis.pipeline(MutualFollowsSet(followed.pk).add_to_set(following.pk))
        pipe.execute()

@celery.task(name='profiles.tasks.remove_mutual_follow')
def remove_mutual_follow(unfollowing, unfollowed):
    from profiles.sets import MutualFollowsSet
    from lib.sets import RedisObject
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    redis.pipeline(MutualFollowsSet(unfollowing.pk).remove_from_set(unfollowed.pk))
    redis.pipeline(MutualFollowsSet(unfollowed.pk).remove_from_set(unfollowing.pk))
    pipe.execute()

@celery.task(name='profiles.tasks.refresh_user_followers_count')
def refresh_user_followers_count(user):
    from stats.sets import UserStats
    followers_count = user.get_followers_count()
    UserStats(user.pk).set(followers_count, "followers")

@celery.task(name='profiles.tasks.refresh_user_stories_counts')
def refresh_user_stories_counts(user):
    from lib.sets import RedisObject
    from stats.sets import UserStats
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    try:
        pub, draft = user.get_stories_count()
    except:
        pub = draft = 0
    if pub:
        redis.pipeline(UserStats(user.pk).set(pub, "stories"))
    if draft:
        redis.pipeline(UserStats(user.pk).set(draft, "drafts"))
    pipe.execute()

