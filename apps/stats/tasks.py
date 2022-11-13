from __future__ import division
import celery
import datetime
from django.contrib.auth import get_user_model
from lib.cache import get_object_from_pk
from django.http import HttpResponse
from django.db.models import Sum, Count
from .sets import *


# Truncate list of unique IPs (per user) for read/royalties figurin'
@celery.task(name='stats.tasks.truncate_unique_ip_lists')
def truncate_unique_ip_lists():
    import time
    from datetime import datetime, timedelta
    from lib.utils import queryset_iterator
    from stats.sets import UserMonthlyUniques
    from django.contrib.auth import get_user_model
    from django.db.models import Sum, Count
    User = get_user_model()

    month_ago = datetime.now() - timedelta(days=7)
    date_string = month_ago.strftime("%Y-%m-%d")
    range_max = time.mktime(time.strptime(date_string, "%Y-%m-%d"))

    users = queryset_iterator(User.objects.all())
    for user in users:
        UserMonthlyUniques(user.pk).trim_set(range_max)

''' For date-range sets (eg top stories over 7d), we increment in real-time,
    then recount nightly for the desired range, for each member of the set.'''
@celery.task(name='stats.tasks.truncate_reads_sets')
def truncate_reads_sets(set_type, days):
    from datetime import datetime, timedelta
    from lib.sets import RedisObject
    from articles.sets import GlobalMostReadStories
    from django.db.models import Sum, Count
    from articles.models import Article

    date_target = datetime.now() - timedelta(days=days)
    date_string = date_target.strftime("%Y-%m-%d")

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()

    # build the date range we're aggregating against
    values = []
    i = 0
    while i < days:
        yesterday = datetime.now() - timedelta(days=i)
        date_string = yesterday.strftime("%Y-%m-%d")
        values.append(date_string)
        i+=1

    if set_type == "stories":
        stories_with_7d_reads = GlobalMostReadStories(days).get_full_set()
        GlobalMostReadStories(days).clear_set()
        for story in stories_with_7d_reads:
            fetch = redis.hmget('s:d:story:reads:%s' % story, values)
            fetch_as_floats = [float(i or 0) for i in fetch]
            sum_of_reads = sum(fetch_as_floats)
            if sum_of_reads:
                redis.pipeline(GlobalMostReadStories().add_to_set(story, sum_of_reads))
    pipe.execute()



# Task to immediately process local events
@celery.task(name='stats.tasks.process_local_stats_event')
def process_local_stats_event(event, request=None):
    from lib.utils import get_client_ip
    from stats.utils import set_active_users
    from articles.models import Article
    from lib.cache import get_object_from_pk
    from django.contrib.auth import get_user_model
    User = get_user_model() 

    # let's add a date
    if not 'date' in event:
        event['date'] = datetime.date.today().strftime("%Y-%m-%d")
    
    if request:
        # try to add the request ip address
        try:
            event['ip'] = get_client_ip(request)
        except:
            event['ip'] = None
    
    event_type = event['event']
    # Log this event:
    StatsFullDailyEventList(event['date']).add_to_list(event)

    # Follows
    if event_type is "followers":
        followed = event['followed']
        follower = event['follower']
        value = event['value']
        foltype = event['foltype']

        if foltype is "user":
            try:
                user = get_object_from_pk(User, followed, False)
                count = user.get_followers_count()
                UserStats(followed).set(count, event_type)
                UserDailyStatsUserFollows("glo").increment(value)    
            except:
                pass
        elif foltype is "suite":
            SuiteStats(followed).increment(value, event_type)
            UserDailyStatsSuiteFollows("glo").increment(value)

    # Responses
    elif event_type is "responses":
        story = event['story']
        parent = event['parent']
        parent_author = event['parent_auth']
        value = event['value']
        responder = event['responder']

        StoryStats(parent).increment(value, event_type)
        UserStats(parent_author).increment(value, event_type)

        UserDailyStatsResponses(parent_author).increment(value)
        UserDailyStatsResponses("glo").increment(value) # global  

    # New posts
    elif event_type is "stories": # story object
        story = event['story']
        author = event['author']
        value = event['value']
        date = event['date']
        
        UserStats(author).increment(value, event_type)
        UserDailyStatsPosts(author).increment(value, date)
        UserDailyStatsPosts("glo").increment(value, date) # global 

        # is this a new user's first post?
        articles_by_author = Article.objects.published().filter(author__pk=author).count()

        # if so, recount active_users
        if articles_by_author == 1:
            set_active_users(event['date']) 

    return HttpResponse('ok')


@celery.task(name='stats.tasks.process_stats_inbox')
def process_stats_inbox(reprocess=False, reprocess_events=None):
    import json
    import datetime
    import time
    from lib.sets import RedisObject
    from lib.enums import EPOCH_ID
    from stats.utils import get_active_inverse

    ''' 
    Except when manually triggered by a reprocess=True cue, this task runs every 30s.
    It empties the current event inbox and processes events from an isolated "processing" list. 

        0) rename inbox > processing
        1) get the event_type
        2) depending on the event, add to sets (pipeline)
        3) execute redis pipeline
        4) add the items to an overall event list, keyed to the event date_string
        5) delete processing
    '''
    if not reprocess:
        key = StatsProcessingIndex().increment()

        processing_key = StatsEventProcessing(key).get_key()
        try:
            StatsEventInbox().rename(processing_key)
        except:
            # There are no events (can't find Inbox key). Let's back out and stop.
            key = StatsProcessingIndex().increment(-1)
    else:
        key = 1

    # Setup pipeline
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    # # Fake some IP addresses for testing
    # i = 0
    # while i < 42:
    #     yesterday = datetime.datetime.now() - datetime.timedelta(days=i)
    #     date_string = yesterday.strftime("%Y-%m-%d")
    #     print(date_string)
    #     redis.zadd("s:uniques:7444", "10.222.333.%s" % i, time.mktime(time.strptime(date_string, "%Y-%m-%d")))
    #     i+=1

    num_events = 0
    num_pipeline_transactions = 0
    while key > 0:
        if not reprocess:
            raw_events = StatsEventProcessing(key).get_list()
        else:
            raw_events = reprocess_events
        # Now, iterate over these events and add to the pipeline
        for re in raw_events:
            value = int(1) # baseline value unless overridden below  .
            num_events += 1
            event = json.loads(re)
            glob_value = value

            try:
                event_type = event['event']
                date = event['date']

                if event_type == "reads" or event_type == "pvs":
                    story = event['story']
                    user_id = event['user'] 
                    archive = True if int(story) < EPOCH_ID else False

                    try:
                        royal = event['royal']
                    except:
                        royal = False
                              
                    try:
                        ip = event['ip']
                    except:
                        ip = None

                    # Note the ordering of attributes - hincrby (key, field, increment) vs zincrby (key, increment, member)
                    if event_type == "reads":
                        pipe.hincrbyfloat("s:d:u:reads:glo",date,glob_value) # global read events
                        pipe.hincrbyfloat("s:d:u:reads:%s" % user_id,date,value) # user daily reads                        
                        pipe.hincrbyfloat("s:t:u:%s" % user_id,event_type,value) # user total stats
                        pipe.hincrbyfloat("s:t:story:%s" % story,event_type,value) # story total stats
                        pipe.hincrbyfloat("s:d:story:reads:%s" % story,date,value) # story daily reads
                        if not archive:
                            pipe.zincrby("story:top:reads:7", story, value) # top stories this week
                            num_pipeline_transactions += 1
                        num_pipeline_transactions += 5
                        
                    elif event_type == "pvs":
                        pipe.hincrbyfloat("s:d:u:pvs:glo",date,glob_value)
                        pipe.hincrbyfloat("s:d:u:pvs:%s" % user_id,date,value)
                        pipe.hincrbyfloat("s:t:u:%s" % user_id,event_type,value)
                        pipe.hincrbyfloat("s:t:story:%s" % story,event_type,value)
                        pipe.hincrbyfloat("s:d:story:pvs:%s" % story,date,value)
                        num_pipeline_transactions += 5                        
                        if royal:
                            pipe.hincrbyfloat("s:d:u:mon:pvs:glo",date,value) # monetized pvs
                            num_pipeline_transactions += 1

                        if ip:
                            try:
                                ip_exists = redis.zscore("s:uniques:%s" % user_id, ip)
                                if not ip_exists:
                                    pipe.zadd("s:uniques:%s" % user_id, ip, time.mktime(time.strptime(date, "%Y-%m-%d"))) # try adding to set of distinct ips that read this AUTHOR this month - returns 1 if true
                                    num_pipeline_transactions += 1
                                    # we truncate this sorted set by time score (zremrangebyscore) each night
                            except Exception as e:
                                print(e)
                                             
                        if not ip_exists: 
                            pipe.hincrbyfloat("s:d:u:uniques:%s" % user_id,date,value) # user daily unique views  
                            pipe.hincrbyfloat("s:d:story:uniques:%s" % story,date,value) # story daily unique views                        
                            num_pipeline_transactions += 3                            

                elif event_type == "profileviews":   
                    user_id = event['user']                 
                    pipe.hincrbyfloat("s:d:u:profileviews:%s" % user_id,date,value)
                    pipe.hincrbyfloat("s:t:u:%s" % user_id,event_type,value)
                    num_pipeline_transactions += 3

                elif event_type == "suiteviews":
                    suite_id = event['suite']
                    pipe.hincrbyfloat("s:d:suite:views:glo",date,value)
                    pipe.hincrbyfloat("s:d:suite:views:%s" % suite_id,date,value)
                    pipe.hincrbyfloat("s:t:u:%s" % suite_id,event_type,value)
                    num_pipeline_transactions += 3

                redis.pipeline(StatsFullDailyEventList(date).add_to_list(re)) # daily log of processed events
                num_pipeline_transactions += 1

            except Exception as e:
                redis.pipeline(StatsFailedEventList().add_to_list(re)) # daily log of failed events
                num_pipeline_transactions += 1

        StatsEventProcessing(key).delete()    
        redis.pipeline(StatsEventProcessing(key).delete()) # remove the current processing bin

        pipe.execute()
        if not reprocess:
            key = StatsProcessingIndex().increment(-1)
        else:
            key -= 1

# If we can't connect to the redis server, store the event in Postgres
@celery.task(name='stats.tasks.add_to_event_overflow')
def add_to_event_overflow(event):
    from .models import EventOverflow

    try:
        EventOverflow.objects.create(event=event)
        print('added an event to the backup')
    except Exception as e:
        print(e)