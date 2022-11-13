from __future__ import division
import datetime
import time
from django.views.generic.base import View
from django.http import Http404, HttpResponse
from django.conf import settings
from lib.utils import get_client_ip, suite_render
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import patch_cache_control
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from articles.models import Article
from lib.utils import get_serialized_list, api_serialize_resource_obj
from lib.cache import get_object_from_pk
from dateutil import parser
from lib.enums import *
from stats.sets import *
import json

class StatsEventRouter(View):
    def dispatch(self, request, *args, **kwargs):
        return super(StatsEventRouter, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from .tasks import add_to_event_overflow
        from .sets import StatsEventInbox
        start_time = time.time() # start stopwatch
        
        # copy the QueryDict so we can manipulate it
        event = request.POST.copy()

        # get an accurate server date into the event               
        event['date'] = datetime.date.today().strftime("%Y-%m-%d")

        # try to add the request ip address
        try:
            event['ip'] = get_client_ip(request)
        except:
            event['ip'] = None

        # try to get the initial referrer
        try:
            event['ref'] = get_initial_referer(request)
        except:
            event['ref'] = None

        try:
            StatsEventInbox().add_to_list(json.dumps(event))
        except:
            # can't connect to redis, so we write the event to Postgres to be processed later
            add_to_event_overflow(json.dumps(event))

        return HttpResponse('ok')

class UnreadBeaconView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(UnreadBeaconView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        notifs = int(request.user.get_unread_notifs_count())
        # chats = int(UserUnreadChatSet(request.user.pk).get_set_count()) or 0
        # total = notifs + chats
        response = {
            # 'notifs': notifs,
            # 'chats': chats,
            'beacon': notifs
        }
        return self.render_to_json_response(response)
        
class AdminStatsView(AjaxableResponseMixin, TemplateView):
    template_name = 'admin/admin_stats_detail.html'
    user = None

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_staff))
    def dispatch(self, *args, **kwargs):
        self.admin_user = 'glo'
        return super(AdminStatsView, self).dispatch(*args, **kwargs)
 
    def daterange(self, start_date, end_date):
        for n in range(int ((end_date - start_date).days)):
            yield start_date + datetime.timedelta(n)

    def fetch_top_stories(self, page=1):
        from articles.sets import UserTempTopStories
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()

        def get_keys():
            return UserTempTopStories("%s:%s" % (self.time_period, self.admin_user)).get_set(self.page_num)

        def add_to_sets(story_loop):
            keys_per_loop = 2
            fetch = pipe.execute()
            adding = len(fetch)
            local_loop = 0 
            while local_loop < adding and story_loop < num_stories:
                story_pk = story_pks[story_loop]
                views_in_period = int(round(sum([float(i or 0) for i in fetch[local_loop]]),0))
                reads_in_period = int(round(sum([float(i or 0) for i in fetch[local_loop+1]]),0))

                data = '%s|%s|%s' % (story_pk, views_in_period, reads_in_period)
                pipe.zadd("story:temp:top:%s:%s" % (self.time_period, self.admin_user), data, reads_in_period) 
                pipe.expire("story:temp:top:%s:%s" % (self.time_period, self.admin_user), 300) # hold onto this for 5 minutes

                story_loop += 1
                local_loop += keys_per_loop

            pipe.execute()

        key_pairs = get_keys()

        if not key_pairs and not page > 1:
            stopwatch_start = time.time()
            fetched_date_range = self.fetch_date_range()
            date_range = fetched_date_range
            
            story_pks = Article.objects.published().filter(author__approved=True, author__is_active=True, created__gte=self.epoch).values_list('pk', flat=True)
            num_stories = len(story_pks)

            loop_threshold = 300
            current_loop = 0
            story_loop = 0
            cumulative_story_loop = 0
            total_loops = num_stories - 1
            for story_pk in story_pks:
                current_loop += 1
                pipe.hmget('s:d:story:pvs:%s' % story_pk, date_range) # views
                pipe.hmget('s:d:story:reads:%s' % story_pk, date_range) # reads
            
                if current_loop == loop_threshold or story_loop == total_loops:
                    add_to_sets(cumulative_story_loop)
                    cumulative_story_loop = story_loop
                
                story_loop += 1

            key_pairs = get_keys()

        return key_pairs         


    def unpack_top_stories(self, top_story_key_pairs):
        stats = {}
        story_pks = []

        start = (self.page_num - 1) * DEFAULT_PAGE_SIZE
        end = self.page_num * DEFAULT_PAGE_SIZE

        for key in top_story_key_pairs:
            split_key = key.split('|')
            story_pks.append(split_key[0])
            stats[split_key[0]] = {
                'views': split_key[1],
                'reads': split_key[2]
                }

        if story_pks:
            objects = get_serialized_list(self.request, story_pks, 'story:mini')
            for obj in objects:
                obj['views'] = stats[str(obj['id'])]['views']
                obj['reads'] = stats[str(obj['id'])]['reads']
            return objects

    def fetch_date_range(self):
        date_range = []
        for d in self.daterange(self.start_date, self.end_date):
            date = d.strftime("%Y-%m-%d")
            stamp = int(time.mktime(d.timetuple()))*1000
            date_range.append(date)

        return date_range

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        fetch_type = request.GET.get('type', '')
        fetch_user_top_stories = True if fetch_type == 'topstories' else False
        self.epoch = parser.parse(SUITE_EPOCH)

        self.page_num = int(request.GET.get('page', '1'))

        start_range = 30   
        self.time_period = request.GET.get('timeperiod', start_range)

        if self.time_period == 'all':
            self.start_date = self.epoch
        else:
            self.start_date = datetime.datetime.now() - datetime.timedelta(days=int(self.time_period))
        self.end_date = datetime.datetime.now() 

        if fetch_user_top_stories:
            key_pairs = self.fetch_top_stories(self.page_num)
            if not key_pairs:
                raise Http404

            objects = self.unpack_top_stories(key_pairs)                        

            if not objects:
                raise Http404

            return self.render_to_json_response({
                "objects": objects
            })

        return super(AdminStatsView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        import time
        from calendar import monthrange
        from dateutil.rrule import rrule, DAILY
        from django.contrib.auth import get_user_model
        from lib.utils import get_serialized_list
        from lib.sets import RedisObject
        from stats.sets import UserDailyStatsReads, UserDailyStatsPageviews, UserDailyStatsPosts, UserDailyStatsProfileViews
        from django.template.loader import render_to_string

        User = get_user_model()

        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()

        series_target = request.POST.get('target','') 
        series_users = True if series_target == 'users' else False
        series_posts = True if series_target == 'globalposts' else False
        series_reads = True if series_target == 'globalreads' else False
        
        fetch_user_top_stories = True if request.POST.get('topstories', '') == 'true' else False
        self.page_num = int(request.POST.get('page', '1'))
        self.target_month = request.POST.get('targetmonth', '')

        start_range = 30   
        self.time_period = request.POST.get('timeperiod', start_range)

        # Get range details
        if self.time_period == 'all':
            start = self.epoch
        else:
            start = datetime.datetime.now() - datetime.timedelta(days=int(self.time_period))            
        finish = datetime.datetime.now()

        if series_users:
            all_users_output = []
            active_users_output = []
            active_ratio_output = []

            total_users = 0
            total_active_users = 0

            all_users_stats = pipe.hgetall("s:d:u:glo:all") # [0]
            all_active_users_stats = pipe.hgetall("s:d:u:glo:active") # [1]
            all_active_ratio_stats = pipe.hgetall("s:d:u:glo:active:ratio") # [2]

            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000
                try:
                    all_users_value = float(fetched[0][d])
                except:
                    all_users_value = float(0)
                try:
                    active_users_value = int(fetched[1][d])
                except:
                    active_users_value = int(0)           
                try:
                    active_ratio_value = float(fetched[2][d])
                except:
                    active_ratio_value = 0

                all_users_output.append([stamp,all_users_value])
                active_users_output.append([stamp,active_users_value])
                active_ratio_output.append([stamp,active_ratio_value])

                total_users += all_users_value
                total_active_users += active_users_value
                
            chart_data = {
                "allusers": all_users_output,
                "activeusers": active_users_output,
                "activeratio": active_ratio_output
            }

            if total_users:
                summary_ratio = total_active_users / total_users
                
            summary_data = {
                "users": True,
                "allusers": round(total_users,0),
                "activeusers": round(total_active_users,0),
                "activeratio": round(summary_ratio,3) if total_users else 0
            }

            return self.render_to_json_response({
                "summary": summary_data,
                "chartdata": chart_data
            })

        if series_posts:
            all_posts_output = []
            approved_posts_output = []
            responses_output = []
            ext_responses_output = []

            total_posts = 0
            total_approved_posts = 0
            total_responses = 0
            total_ext_responses = 0

            all_posts_stats = pipe.hgetall("s:d:admin:posts:all") # [0]
            all_approved_posts_stats = pipe.hgetall("s:d:admin:posts:approved") # [1]
            all_responses_stats = pipe.hgetall("s:d:admin:posts:responses") # [2]
            all_ext_responses_stats = pipe.hgetall("s:d:admin:posts:responses:ext") # [3]

            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000
                try:
                    all_posts_value = float(fetched[0][d])
                except:
                    all_posts_value = float(0)
                try:
                    approved_posts_value = int(fetched[1][d])
                except:
                    approved_posts_value = int(0)           
                try:
                    responses_value = float(fetched[2][d])
                except:
                    responses_value = 0
                try:
                    ext_responses_value = float(fetched[3][d])
                except:
                    ext_responses_value = 0

                all_posts_output.append([stamp,all_posts_value])
                approved_posts_output.append([stamp,approved_posts_value])
                responses_output.append([stamp,responses_value])
                ext_responses_output.append([stamp,ext_responses_value])

                total_posts += all_posts_value
                total_approved_posts += approved_posts_value
                total_responses += responses_value
                total_ext_responses += ext_responses_value
                
                
            chart_data = {
                "allposts": all_posts_output,
                "approvedposts": approved_posts_output,
                "responses": approved_posts_output,
                "extresponses": approved_posts_output
            }

            summary_data = {
                "globalposts": True,
                "allposts": round(total_posts,0),
                "approvedposts": round(total_approved_posts,0),
                "responses": round(total_responses,0),
                "extresponses": round(total_ext_responses,0)
            }

            return self.render_to_json_response({
                "summary": summary_data,
                "chartdata": chart_data
            })

        if series_reads:
            read_stats_output = []
            pageviews_stats_output = []

            total_reads = 0
            total_pageviews = 0

            all_reads_stats = pipe.hgetall("s:d:u:reads:%s" % self.admin_user) # [0]
            all_pvs_stats = pipe.hgetall("s:d:u:pvs:%s" % self.admin_user) # [1]

            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000

                try:
                    reads_value = float(fetched[0][d])
                except:
                    reads_value = float(0)
                try:
                    pvs_value = int(fetched[1][d])
                except:
                    pvs_value = int(0)           

                total_reads += reads_value
                total_pageviews += pvs_value

                read_stats_output.append([stamp,int(round(reads_value,0))])
                pageviews_stats_output.append([stamp,pvs_value])

            chart_data = {
                "reads": read_stats_output,
                "pageviews": pageviews_stats_output
            }

            summary_data = {
                "globalreads": True,
                "reads": round(total_reads,0),
                "pageviews": round(total_pageviews,0),
                "rate": round((total_reads / total_pageviews),1) if total_pageviews else 0,
            }

            return self.render_to_json_response({
                "summary": summary_data,
                "chartdata": chart_data
            })

        return HttpResponse('ok')

    def get_context_data(self, **kwargs):
        context = super(AdminStatsView, self).get_context_data(**kwargs)
        context['stats_json_obj'] = json.dumps({ 'test': 'this is a test'})
        context['stats_rendered'] = suite_render(self.request, 'admin-stats-shell', context['stats_json_obj'])
        return context

class UserStatsView(AjaxableResponseMixin, TemplateView):
    template_name = 'profiles/stats_detail.html'
    user = None

    def dispatch(self, *args, **kwargs):
        if not self.user:
            self.user = self.request.user
        self.epoch = parser.parse(SUITE_EPOCH)
        return super(UserStatsView, self).dispatch(*args, **kwargs)
 
    def daterange(self, start_date, end_date):
        for n in range(int ((end_date - start_date).days)):
            yield start_date + datetime.timedelta(n)

    def fetch_top_stories(self, sort_type):
        # s:d:story:w:added
        from articles.sets import UserTempTopStories
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection(slave=False)
        pipe = redis.pipeline()
        if not sort_type:
            sort_type = 'reads'

        def get_keys():
            if sort_type == 'reads':
                self.temp_key = 's:temp:story:top:reads:%s:%s' % (self.time_period, self.user.pk)
            elif sort_type == 'activity':
                self.temp_key = 's:temp:story:top:act:%s:%s' % (self.time_period, self.user.pk)
        
            start = DEFAULT_PAGE_SIZE * (self.page_num - 1)
            stop = (self.page_num * DEFAULT_PAGE_SIZE) - 1
            return redis.zrevrange(self.temp_key, start, stop, withscores=False)

        def add_to_sets(story_loop):
            keys_per_loop = 2
            fetch = pipe.execute()
            adding = len(fetch)
            local_loop = 0 
            while local_loop < adding and story_loop < num_stories:
                story_pk = story_pks[story_loop]

                # if sort_type == 'reads': 
                #     stats_keys = ['s:d:story:pvs', 's:d:story:reads']
                # elif sort_type == 'activity':
                #     stats_keys = ['s:d:story:w:added', 's:d:story:w:removed']

                d1 = int(round(sum([float(i or 0) for i in fetch[local_loop]]),0)) # views or words removed
                d2 = int(round(sum([float(i or 0) for i in fetch[local_loop+1]]),0)) # reads or words added

                hashed_data = '%s|%s|%s' % (story_pk, d1, d2)
                pipe.zadd(self.temp_key, hashed_data, d2) 
                pipe.expire(self.temp_key, 3600) # expire after 1hr

                story_loop += 1
                local_loop += keys_per_loop

            pipe.execute()

        key_pairs = get_keys()

        if not key_pairs and not self.page_num > 1:
            fetched_date_range = self.fetch_date_range()
            date_range = fetched_date_range            
            story_pks = Article.objects.all().exclude(status='deleted').filter(author=self.user).values_list('pk', flat=True)
            num_stories = len(story_pks)

            if sort_type == 'reads': 
                stats_keys = ['s:d:story:pvs', 's:d:story:reads']
            elif sort_type == 'activity':
                stats_keys = ['s:d:story:w:added', 's:d:story:w:removed']

            loop_threshold = 300
            current_loop = 0
            story_loop = 0
            cumulative_story_loop = 0
            total_loops = num_stories - 1
            for story_pk in story_pks:
                current_loop += 1

                for sk in stats_keys:
                    pipe.hmget(sk + ':%s' % story_pk, date_range)

                if current_loop == loop_threshold or story_loop == total_loops:
                    add_to_sets(cumulative_story_loop)
                    cumulative_story_loop = story_loop
                
                story_loop += 1

            key_pairs = get_keys()

        return key_pairs         


    def unpack_top_stories(self, top_story_key_pairs, sort_type):
        if not sort_type:
            sort_type = 'reads'

        if sort_type == 'reads': 
            field_names = ['views', 'reads']
        elif sort_type == 'activity':
            field_names = ['removed', 'added']

        stats = {}
        story_pks = []
        # objs = get_serialized_list(self.request, story_pks, 'story:mini')

        start = (self.page_num - 1) * DEFAULT_PAGE_SIZE
        end = self.page_num * DEFAULT_PAGE_SIZE


        for key in top_story_key_pairs:
            split_key = key.split('|')
            story_pks.append(split_key[0])
            stats[split_key[0]] = {
                field_names[0]: split_key[1],
                field_names[1]: split_key[2]
                }

        if story_pks:
            order = ((self.page_num - 1) * DEFAULT_PAGE_SIZE) + 1 if self.page_num > 1 else self.page_num
            objects = get_serialized_list(self.request, story_pks, 'story:mini')
            for obj in objects:
                obj['order'] = order
                obj[field_names[0]] = stats[str(obj['id'])][field_names[0]]
                obj[field_names[1]] = stats[str(obj['id'])][field_names[1]]
                order += 1;
            return objects

    def fetch_date_range(self):
        date_range = []
        if self.time_period == 'all':
            if self.user.date_joined < self.epoch:
                start_date = self.epoch
            else:
                start_date = self.user.date_joined
        else:
            start_date = datetime.datetime.now() - datetime.timedelta(days=int(self.time_period))
        end_date = datetime.datetime.now() 

        for d in self.daterange(start_date, end_date):
            date = d.strftime("%Y-%m-%d")
            stamp = int(time.mktime(d.timetuple()))*1000
            date_range.append(date)

        return date_range

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()

        fetch_type = request.GET.get('type', '')
        fetch_user_top_stories = True if fetch_type == 'topstories' else False
        # fetch_user_top_stories = True if request.GET.get('topstories', '') == 'true' else False
        self.page_num = int(request.GET.get('page', '1'))

        self.target_month = request.GET.get('targetmonth', '')

        start_range = 30   
        self.time_period = request.GET.get('timeperiod', start_range)

        if fetch_user_top_stories:
            sort_type = request.GET.get('sort', '')
            key_pairs = self.fetch_top_stories(sort_type)
            if not key_pairs:
                raise Http404

            objects = self.unpack_top_stories(key_pairs, sort_type)                        

            if not objects:
                raise Http404

            return self.render_to_json_response({
                "objects": objects
            })

        return super(UserStatsView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        import time
        from random import randrange
        from calendar import monthrange
        from dateutil.rrule import rrule, DAILY
        from django.contrib.auth import get_user_model
        from lib.utils import get_serialized_list
        from lib.sets import RedisObject
        from stats.sets import UserDailyStatsReads, UserDailyStatsPageviews, UserDailyStatsPosts, UserDailyStatsProfileViews
        from django.template.loader import render_to_string

        User = get_user_model()

        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()

        series_target = request.POST.get('target','') 
        series_posts = True if series_target == 'posts' else False
        series_activity = True if series_target == 'activity' else False

        series_single_story = True if series_target == 'sec-story' else False
        fetch_user_top_stories = True if request.POST.get('topstories', '') == 'true' else False
        
        self.content_id = request.POST.get('contentid', '')
        self.page_num = int(request.POST.get('page', '1'))
        self.target_month = request.POST.get('targetmonth', '')

        start_range = 30   
        self.time_period = request.POST.get('timeperiod', start_range)

        # Get range details

        if self.time_period == 'all':
            if self.user.date_joined < self.epoch:
                start = self.epoch
            else:
                start = self.user.date_joined
        else:
            start = datetime.datetime.now() - datetime.timedelta(days=int(self.time_period))            
        finish = datetime.datetime.now()

        if series_posts:
            views_output = []
            retention_output = []
            repeats_output = []
            responses_output = []

            total_reads = 0
            total_pageviews = 0
            total_uniques = 0
            total_responses = 0

            all_reads_stats = pipe.hgetall("s:d:u:reads:%s" % self.user.pk) # [0]
            all_pvs_stats = pipe.hgetall("s:d:u:pvs:%s" % self.user.pk) # [1]
            all_uniques_stats = pipe.hgetall("s:d:u:uniques:%s" % self.user.pk) # [2]
            all_responses_stats = pipe.hgetall("s:d:u:resps:%s" % self.user.pk) # [3]

            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000

                try:
                    reads_value = float(fetched[0][d])
                except:
                    reads_value = float(0)
                try:
                    pvs_value = float(fetched[1][d])
                except:
                    pvs_value = float(0)           
                try:
                    uniques_value = float(fetched[2][d])
                except:
                    uniques_value = float(0)
                # try:
                #     responses_value = float(fetched[3][d])
                # except:
                #     responses_value = float(0)                

                # for testing
                responses_value = randrange(0,10)

                total_reads += reads_value
                total_pageviews += pvs_value
                total_uniques += uniques_value
                total_responses += responses_value

                
                retention = 0.0
                if reads_value and pvs_value:
                    retention = reads_value/pvs_value
                repeats = 0
                if uniques_value and pvs_value:
                    repeats = 1.0 - (uniques_value/pvs_value)

                views_output.append([stamp,int(round(pvs_value,0))])
                retention_output.append([stamp,round(retention,2)])
                repeats_output.append([stamp,round(repeats,2)])
                responses_output.append([stamp,int(round(responses_value,0))])

            chart_data = {
                "pageviews": views_output,
                "retention": retention_output,
                "repeats": repeats_output,
                "responses": responses_output,             
            }

            from django.contrib.humanize.templatetags.humanize import intcomma
            def shortenNum(num):
                magnitude = 0
                while abs(num) >= 1000:
                    magnitude += 1
                    num /= 1000.0
                return '%.1f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

            summary_retention = 0.0
            if total_reads and total_pageviews:
                summary_retention = round(((total_reads / total_pageviews)*100),1)
            summary_repeats = 0.0
            if total_uniques and total_pageviews:
                repeats = round(1.0 - (total_uniques / total_pageviews), 1)

            summary_data = {
                "posts": True,
                "pageviews": shortenNum(round(total_pageviews, 0)),
                "responses": shortenNum(round(total_responses, 0)),
                "retention": summary_retention,
                "repeats": summary_repeats
            }

            return self.render_to_json_response({
                "summary": summary_data,
                "chartdata": chart_data
            })

        elif series_activity:
            words_added_output = []
            words_removed_output = []
            stories_published_output = []

            total_added = 0
            total_removed = 0

            all_added_stats = pipe.hgetall("s:d:u:words:added:%s" % self.user.pk) # [0]
            all_removed_stats = pipe.hgetall("s:d:u:words:removed:%s" % self.user.pk) # [1]
            all_published_stats = pipe.hgetall("s:d:u:posts:%s" % self.user.pk) # [2]
            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000

                try:
                    added_value = float(fetched[0][d])
                except:
                    added_value = float(0)
                try:
                    removed_value = -int(fetched[1][d])
                except:
                    removed_value = int(0)
                try:
                    published_value = float(fetched[2][d])
                except:
                    published_value = 0.0

                words_added_output.append([stamp,int(round(added_value,0))])
                words_removed_output.append([stamp,int(round(removed_value,0))])
                stories_published_output.append([stamp,published_value])

                total_added += added_value
                total_removed += removed_value

            chart_data = {
                "words-added": words_added_output,
                "words-removed": words_removed_output,
                "stories-published": stories_published_output
            }

            summary_data = {
                "activity": True,
                "wordsAdded": total_added,
                "wordsRemoved": total_removed
            }                
            return self.render_to_json_response({
                "chartdata": chart_data,
                "summary": summary_data
            })

        if series_single_story:
            from articles.models import Article
            from articles.api import StoryMiniResource
            read_stats_output = []
            pageviews_stats_output = []
            uniques_stats_output = []

            total_reads = 0
            total_pageviews = 0
            total_uniques = 0

            all_reads_stats = pipe.hgetall("s:d:story:reads:%s" % self.content_id) # [0]
            all_pvs_stats = pipe.hgetall("s:d:story:pvs:%s" % self.content_id) # [1]
            all_uniques_stats = pipe.hgetall("s:d:story:uniquereads:%s" % self.content_id) # [2]

            fetched = pipe.execute()  

            # Iterate over entire range
            for dt in rrule(DAILY, dtstart=start, until=finish):
                d = dt.strftime("%Y-%m-%d")
                stamp = int(time.mktime(dt.timetuple()))*1000

                try:
                    reads_value = float(fetched[0][d])
                except:
                    reads_value = float(0)
                try:
                    pvs_value = float(fetched[1][d])
                except:
                    pvs_value = float(0)           
                try:
                    uniques_value = float(fetched[2][d])
                except:
                    uniques_value = float(0)
                    
                total_reads += reads_value
                total_pageviews += pvs_value
                total_uniques += uniques_value

                read_stats_output.append([stamp,int(round(reads_value,0))])
                uniques_stats_output.append([stamp,int(round(uniques_value,0))])
                pageviews_stats_output.append([stamp,int(round(pvs_value,0))])

            chart_data = {
                "reads": read_stats_output,
                "pageviews": pageviews_stats_output,
                "uniques": uniques_stats_output
            }

            story = get_object_from_pk(Article, self.content_id, False)
            content_object = api_serialize_resource_obj(story, StoryMiniResource(), request)

            summary_data = {
                "posts": True,
                "reads": round(total_reads,0),
                "pageviews": round(total_pageviews,0),
                "rate": round((total_reads / total_pageviews),1) if total_pageviews else 0,
                "uniques": round(total_uniques,0)
            }

            return self.render_to_json_response({
                "summary": summary_data,
                "chartdata": chart_data,
                "contentObj": content_object
            })
            

        return HttpResponse('ok')

    def get_context_data(self, **kwargs):
        context = super(UserStatsView, self).get_context_data(**kwargs)
        context['stats_json_obj'] = json.dumps({ 'test': 'this is a test'})
        context['stats_rendered'] = suite_render(self.request, 'stats-shell', context['stats_json_obj'])
        return context
