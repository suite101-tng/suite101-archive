from __future__ import division
import datetime
from dateutil import parser
from django.views.generic.base import View
from django.http import Http404, HttpResponse
from project import settings
from django.contrib.contenttypes.models import ContentType
from lib.utils import get_client_ip
from django.contrib.auth import get_user_model
from profiles.models import SuiteUser
import json
from stats.sets import StatsEventInbox

def percentage(value):  
    try:  
        return round((value * 100),1)
    except ValueError:  
        return '' 

def set_active_users(date_string):
    from lib.enums import SUITE_EPOCH, CURRENT_RANGE
    from lib.sets import RedisObject
    from stats.sets import UserDailyStatsUsersCount, UserDailyStatsActiveCount, UserDailyStatsActiveRatio

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()
    
    is_current_threshold = parser.parse(date_string) - datetime.timedelta(days=int(CURRENT_RANGE))

    active_users = SuiteUser.objects.filter(is_active=True, last_pub_date__gte=is_current_threshold, last_pub_date__lte=date_string).count()
    all_users = SuiteUser.objects.filter(is_active=True, date_joined__gte=SUITE_EPOCH, date_joined__lte=date_string).count()
    ratio = float(active_users/all_users)

    redis.pipeline(UserDailyStatsUsersCount().set(all_users, date_string))
    redis.pipeline(UserDailyStatsActiveCount().set(active_users, date_string))
    redis.pipeline(UserDailyStatsActiveRatio().set(ratio, date_string))   
    pipe.execute()   
    return ratio

def get_active_inverse(date_string=None):
    # get or set daily active users ratio
    from stats.sets import UserDailyStatsActiveRatio
    from lib.enums import SUITE_EPOCH, CURRENT_RANGE
    if not date_string:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        date_string = yesterday.strftime("%Y-%m-%d")
    active_ratio = UserDailyStatsActiveRatio().get(date_string)
    if not active_ratio:
        active_ratio = set_active_users(date_string)
    return (1.0/float(active_ratio))

