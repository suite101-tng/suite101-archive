from __future__ import division
import csv
import datetime, time
from dateutil import parser
from random import randrange, uniform
from django.db.models import Sum, Count
from lib.utils import queryset_iterator
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from profiles.models import SuiteUser
from articles.models import Article
from stats.sets import UserDailyStatsReads, UserDailyStatsPageviews, UserDailyStatsRoyalties
import json


class Command(BaseCommand):
    help = 'usage: python manage.py stats_test_data <start> <finish> <user_pk>'

    def handle(self, *args, **options):

        redis = RedisObject().get_redis_connection(slave=False) # reading and writing here
        pipe = redis.pipeline()

        def daterange(start_date, end_date):
            for n in range(int ((end_date - start_date).days)):
                yield start_date + datetime.timedelta(n)

        time_limit = datetime.datetime.now() - datetime.timedelta(days=90)
        epoch = datetime.datetime.strptime('2014-08-10', "%Y-%m-%d").date()

        now = time.time()
        start_date = datetime.datetime.strptime(args[0], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(args[1], "%Y-%m-%d").date()

        try:
            user_pk = args[2]
        except:
            user_pk = [7444]


        test_user = SuiteUser.objects.get(pk=user_pk)       
        stories = Article.objects.published().filter(author=test_user).values_list('pk', flat=True)[:50] # archive stories
        for story in stories:

            for d in daterange(start_date, end_date):
                date = d.strftime("%Y-%m-%d")

                views = uniform(4.0,25.0)
                reads = views * uniform(0.2,0.6)
                uniques = reads * uniform(0.1,0.4)

                pipe.hincrbyfloat("s:t:story:%s" % story,'pvs',views) # increment story totals by diff
                pipe.hset("s:d:story:pvs:%s" % story,date,views)                      
                pipe.hincrbyfloat("s:t:u:%s" % test_user.pk,'pvs',views) # increment story totals by diff
                pipe.hincrbyfloat("s:d:u:pvs:%s" % test_user.pk,date,views) # user daily reads       

                pipe.hincrbyfloat("s:t:story:%s" % story,'reads',reads) # increment story totals by diff
                pipe.hset("s:d:story:reads:%s" % story,date,reads) # story daily reads
                                 
                pipe.hincrbyfloat("s:t:u:%s" % test_user.pk,'reads',reads) # increment story totals by diff
                pipe.hincrbyfloat("s:d:u:reads:%s" % test_user.pk,date,reads) # user daily reads       
            
                pipe.hincrbyfloat("s:d:u:uniquereads:%s" % test_user.pk,date,uniques) # user daily unique reads  
                pipe.hincrbyfloat("s:d:u:uniquereads:glo",date, uniques) # global daily unique reads      
                pipe.hincrbyfloat("s:d:story:uniquereads:%s" % story,date,uniques) # story daily unique reads                        

            pipe.execute()  



