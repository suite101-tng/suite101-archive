import datetime,time, logging, json, operator
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import patch_cache_control, never_cache
from django.http import Http404, HttpResponse, HttpResponseNotFound
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.views.generic.detail import DetailView
from django.views.generic import CreateView, DeleteView, UpdateView
from django.views.generic.base import View
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse
from django.db.models import Q      

from stats.tasks import process_local_stats_event
from lib.decorators import ajax_login_required
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.utils import api_serialize_resource_obj, suite_render, get_serialized_list
from lib.views import GenericFollowView, GenericUnFollowView
from lib.tasks import send_email_alert, resize_suite_hero_image
from lib.enums import *
from lib.cache import get_object_from_hash, get_object_from_pk, get_object_from_slug
from articles.models import Article
from links.models import Link
from project import settings
from suites.api import SuiteMiniResource, SuiteResource

from .forms import *
from .models import Suite, SuiteRequest, SuiteInvite, SuiteMember, SuitePost

logger = logging.getLogger(__name__)

class SuiteCreateView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SuiteCreateView, self).dispatch(*args, **kwargs)

    def clean_suite_title(self, suite_title):
        title = suite_title.strip()
        if len(title) > 140:
            title = title[:137] + '...'
        return title

    def clean_suite_description(self, suite_description):
        description = suite_description.strip()
        if len(description) > 140:
            description = description[:137] + '...'
        return description

    def post(self, request, *args, **kwargs):
        from lib.utils import seems_like_email
        from suites.models import SuiteInvite
        from suites.tasks import process_new_suite, fanout_suite_invite
        User = get_user_model()
        suite_title = suite_desc = ''

        title_string = request.POST.get("title", "")  
        if title_string:
            suite_title = self.clean_suite_title(title_string)
        desc_string = request.POST.get("desc", "")
        if desc_string:
            suite_desc = self.clean_suite_description(desc_string)
        suite_is_private = True if request.POST.get("private", "") == 'true' else False
        
        member_string = request.POST.get('members', '')
        suite_members = json.loads(member_string)
        
        email = ''
        email_invite = False
        member_object = None

        if not suite_title:
            raise Http404

        new_suite = Suite.objects.create(name=suite_title, description=suite_desc, owner=request.user, private=suite_is_private)
        SuiteMember.objects.create(suite=new_suite, user=request.user, status="owner")

        if suite_members:
            # invite each of the members in the list; they'll become members if they accept the invitation
            for member in suite_members:
                # email?
                if str('@') in member:
                    if seems_like_email(member):
                        email = member
                        email_invite = True
    
                        # try to get a user object (look for many, pick the first)
                        users_from_email = User.objects.filter(email=email)
                        if users_from_email:
                            if users_from_email[0].contactable(request.user):
                                member_object = users_from_email[0]

                else:
                    try:
                        member_object = get_object_from_pk(User, member['id'], False)    
                    except Exception as e:
                        print(e)
                        continue

                suite_invite, created = SuiteInvite.objects.get_or_create(suite=new_suite, user_inviting=new_suite.owner, user_invited=member_object, email_invite=email_invite, email=email)                
                if member_object:
                    fanout_suite_invite(suite_invite, True)
                
                else:
                    send_email_alert.delay(new_suite.owner, new_suite, request.user)

        result = {
            'suiteId': new_suite.pk,
            'hashedId': new_suite.get_hashed_id()
        }

        process_new_suite(new_suite)
        return self.render_to_json_response(result)

class SuiteMiniCardFetch(AjaxableResponseMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(SuiteMiniCardFetch, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        import random
        import json
        from suites.sets import FeaturedSuiteSet

        mini_suites = []
        suites = FeaturedSuiteSet().get_full_set()[:12]
        if not suites:
            raise Http404

        upper = len(suites)
        indices = random.sample(xrange(0, upper), 3)

        for i in indices:
            mini_suites.append(suites[i])

        return self.render_to_json_response({
                    "suites": get_serialized_list(request, mini_suites,'suite:mini')
                })

class SuiteListView(ListView):
    template_name = 'suites/suite_list.html'
    model = Suite
    paginate_by = DEFAULT_PAGE_SIZE

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, *args, **kwargs):
        if self.request.is_ajax():
            self.template_name = 'suites/_suite_list.html'
        return super(SuiteListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        return Suite.objects.all()

    def get_context_data(self, **kwargs):
        context = super(SuiteListView, self).get_context_data(**kwargs)
        suites_context = []
        for suite in context['object_list']:
            suite_json_obj = api_serialize_resource_obj(suite, SuiteMiniResource(), self.request)
            suites_context.append(suite_json_obj)
        context['suites_rendered'] = suite_render(self.request, 'suite-teaser', suites_context, True)
        return context

class SuiteDetailView(AjaxableResponseMixin, CachedObjectMixin, DetailView):
    model = Suite
    template_name = 'suites/suite_detail.html'
    obj = None
    show_user = True

    def dispatch(self, request, *args, **kwargs):
        self.hashed_id = kwargs.get('hashed_id')
        response = super(SuiteDetailView, self).dispatch(request, *args, **kwargs)
        return response
  
    def get_object(self): 
        self.obj = get_object_from_hash(self.hashed_id)
        if not self.obj.owner.is_active:
            raise Http404
        if self.obj.private:
            if not self.request.user.is_authenticated():
                raise Http404
            elif not self.request.user.member_of(self.obj) and not self.request.user.invited_to(self.obj):
                raise Http404
    
        return self.obj   

    def get(self, request, *args, **kwargs):
        from django.db.models import Q
        from lib.utils import get_serialized_list

        has_page_param = self.request.GET.get('page', None)
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        self.has_next = False
        self.has_prev = False        
        self.feed_type = self.request.GET.get('feedtype', 'stories') 
        self.feed = None

        obj = self.get_object()
        # default - and note: /username/[type] is noindex, follow

        if self.feed_type == "followers":
            self.feed, has_next = obj.get_followers(request, self.page_num)
            self.has_previous = True if self.page_num > 1 else False

        elif self.feed_type == "stories":
            start = (self.page_num - 1) * DEFAULT_PAGE_SIZE
            end = self.page_num * DEFAULT_PAGE_SIZE + 1

            post_pks = obj.get_suite_post_pks(request, self.page_num)

            self.has_next = True if len(post_pks) > DEFAULT_PAGE_SIZE else False
            self.has_previous = True if self.page_num > 1 else False
                            
            if post_pks: 
                self.feed = get_serialized_list(self.request, post_pks,'post:mini')[:DEFAULT_PAGE_SIZE]

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                "objects": self.feed
            })

        return super(SuiteDetailView, self).get(request, args, kwargs)

    def get_reverse_url(self):
        url_name = 'suite_detail'
        # return reverse(url_name, kwargs={'hashed_id': self.object.hashed_id})
        return self.obj.get_absolute_url()

    def get_inner_context(self):
        if not self.spa_fetch:
            innercontext = api_serialize_resource_obj(self.object, SuiteResource(), self.request)
        else:
            innercontext = {}

        if self.feed_type == 'stories':
            innercontext['storyView'] = True
            innercontext['stories'] = self.feed

        elif self.feed_type == 'followers':
            innercontext['followersView'] = True       
            innercontext['followers'] = self.feed   

        if self.has_next:
            next_page_num = self.page_num + 1
            innercontext['nextPage'] = next_page_num
            innercontext['nextLink'] = self.get_reverse_url() + '/stories?page=' + str(next_page_num)

        if self.has_prev:
            prev_page_num = self.page_num - 1
            innercontext['prevPage'] = prev_page_num
            innercontext['prevLink'] = self.get_reverse_url() + '/stories?page=' + str(prev_page_num)

        return innercontext

    def get_context_data(self, **kwargs):
        import time
        from django.template.loader import render_to_string
        context = super(SuiteDetailView, self).get_context_data(**kwargs)
        has_page_param = self.request.GET.get('page')
        page_num = self.request.GET.get('page', '1')
        if not page_num.isdigit():
            raise Http404
        page_num = int(page_num)
        innercontext = self.get_inner_context()

        context['object'] = self.object
        innercontext['showUser'] = True

        context['feed_type'] = self.feed_type

        if self.feed_type == 'stories':
            if page_num < 2:
                context['meta_robots'] = 'index, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url()
            else:
                context['meta_robots'] = '%s, follow, noodp, noydir' % ('index' if self.object.is_indexed else 'noindex')
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(page_num) 
        
        if self.feed_type == 'followers':
            innercontext['followersView'] = True
            context['meta_robots'] = 'noindex, follow, noodp, noydir'
            if page_num > 1:
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(page_num)                
            else:
                context['canonical_link'] = self.get_reverse_url()

            innercontext['followers'] = self.feed

        if page_num > 1:
            context['canonical_link'] = self.get_reverse_url() + '?page=' + str(page_num)
        else:
            context['canonical_link'] = self.get_reverse_url()

        if self.has_next:
            next_page_num = page_num + 1
            context['has_next'] = True
            context['next_link'] = self.get_reverse_url() + '?page=' + str(next_page_num)
        
        if self.has_previous:
            prev_page_num = page_num - 1
            context['has_prev'] = True
            context['prev_link'] = self.get_reverse_url() + '?page=' + str(prev_page_num)

        owner_twitter = "https://twitter.com/%s" % self.object.owner.twitter_username if self.object.owner.twitter_username else ''
        owner_facebook = self.object.owner.facebook_url if self.object.owner.facebook_url else ''
        suite_twitter = "https://twitter.com/suiteio"
        suite_facebook = "https://facebook.com/suitestories"
        try:
            image = self.object.hero_image.get_large_image_url()
        except:
            image = ''
        json_ld = json.dumps({
            "@context":"http://schema.org",
            "@type":"CollectionPage",
            "name":"%s" % self.object.name,
            "description":"%s" % self.object.description or '',
            "url":"https://suite.io%s" % self.object.get_absolute_url(),
            "image": image,
            "editor": {
                "@type": "Person",
                "name": self.object.owner.get_full_name(),
                "sameAs":[ owner_facebook, owner_twitter ]
                },
            "lastReviewed": self.object.modified.strftime('%a %b %d %H:%M:%S +0000 %Y'), 
            "inLanguage":"en-us",
            "publisher": {
                "@type":"Organization",
                "name":"Suite",
                "logo":"",
                "sameAs":[ suite_facebook, suite_twitter ],
                "url":"https://suite.io",
                "founder":{"@type":"Person","name":"Michael Kedda"}
                },
            "location":{"@type":"PostalAddress","addressLocality":"Vancouver","addressRegion":"BC"}

            })
        context['json_ld'] = json_ld
        context['suite_json_str'] = json.dumps(innercontext)
        context['suite_detail_rendered'] = suite_render(self.request, 'suite-detail', innercontext)

        return context


class SuiteImageUploadView(AjaxableResponseMixin, CachedObjectMixin, CreateView):
    form_class = SuiteUploadImageForm
    template_name = 'suites/upload.html'  # doesn't get used.
    success_url = '/'  # doesn't get used.

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SuiteImageUploadView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        from suites.api import SuiteImageResource
        image = form.save(commit=False)
        image.user = self.request.user
        image.save()

        resize_suite_hero_image.delay(image.pk)
        return super(SuiteImageUploadView, self).form_valid(form,
            extra_data={
                'image_url': image.get_orig_image_url(),
                'pk': image.pk,
                'resource_uri': SuiteImageResource().get_resource_uri(image)
            }
        )

class SuiteJoinRequestView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SuiteJoinRequestView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from suites.models import Suite, SuiteInvite, SuiteRequest, SuiteMember
        from suites.tasks import refresh_suite_stats
        from articles.models import Article
        import json

        already_requested = None

        suite = get_object_from_pk(Suite, request.POST.get("suite", ""))  
        message = str(request.POST.get("msg", ""))  


        # todo: if already invited, approve and make the user a member on the spot

        # create the suite request
        suite_request, created = SuiteRequest.objects.get_or_create(suite=suite, user=request.user)

        if not created:
            # Build the status reply for the client
            status = {
                'status': 'alreadyRequested'
            }      
        else:
            # move this here so that we can gracefully handle existing requests in the get_or_create above
            suite_request.message = message 
            suite_request.save()

            # Build the status reply for the client
            status = {
                'status': 'newRequest'
            }

        suite_request.fanout_notification()

        # Also send out an email
        # send_email_alert.delay(self.suite.owner, self.object, self.request.user)
        
        # return HttpResponse(status) 
        return self.render_to_json_response(status)

class SuiteJoinRequestRespondView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.suite_request = get_object_from_pk(SuiteRequest, pk, False)
        return super(SuiteJoinRequestRespondView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        from suites.tasks import fanout_new_suite_member        
        status = int(request.POST.get("stat", ""))   
        user = self.suite_request.user
        
        if not self.suite_request:
            raise Http404

        now = datetime.datetime.now()
        time_score = time.mktime(now.timetuple())

        if status:
            if status == 1:
                # create the SuiteMember object
                suite_member, created = SuiteMember.objects.get_or_create(suite=self.suite_request.suite, user=user)
                suite_member.save()
                
                # update the SuiteRequest object
                self.suite_request.status = 'accepted'

                # fan it out
                fanout_new_suite_member(suite_member)

            if status == 0:
                try:
                    suite_member = SuiteMember.objects.get(suite=self.suite_request.suite, user=user)
                    suite_member.delete()
                except:
                    pass

                # update the SuiteRequest object
                self.suite_request.status = 'rejected'
               
            self.suite_request.invalidate()
            self.suite_request.save()
            self.suite_request.suite.invalidate()

            # add a notification for the person accepted/rejected:
            suite_request.fanout_notification()
            user.invalidate()

        # Clean up stray invites
        try:
            SuiteInvite.objects.filter(suite=self.suite_request.suite, user=user).delete()
        except Exception as e:
            pass

        return HttpResponse('ok')

class SuiteFollowView(GenericFollowView):
    def dispatch(self, *args, **kwargs):
        kwargs['model_object'] = Suite
        return super(SuiteFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.tasks import process_new_follow
        from profiles.sets import UserFollowsSuitesSet
        response = super(SuiteFollowView, self).post(request, *args, **kwargs)
        now = datetime.datetime.now()
        time_score = time.mktime(now.timetuple())
        suite = self.obj
        follower = request.user
        follow = self.obj

        # build and send the stats event
        stat_value = 1
        event = {
            "event": "followers",
            "followed": suite.pk,
            "follower": request.user.pk,
            "foltype": "suite",
            "value": stat_value
        }
        process_local_stats_event(event, self.request)
        process_new_follow(self.follow)
        return response


class SuiteUnFollowView(GenericUnFollowView):
    def dispatch(self, *args, **kwargs):
        kwargs['model_object'] = Suite
        return super(SuiteUnFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.tasks import process_unfollow
        from profiles.sets import UserFollowsSuitesSet
        response = super(SuiteUnFollowView, self).post(request, *args, **kwargs)

        suite = self.obj
        follower = request.user

        follower.invalidate()
        suite.invalidate()
        suite.save()

        # build and send the stats event
        stat_value = -1
        event = {
            "event": "followers",
            "followed": suite.pk,
            "follower": follower.pk,
            "foltype": "suite",
            "value": stat_value
        }
        process_local_stats_event(event, self.request)
        process_unfollow(suite, request.user)

        # Hand off to task to remove this Suite from user's feeds
        return response

class SuiteDeleteView(View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.suite = get_object_from_pk(Suite, request.POST.get('pk'))
        return super(SuiteDeleteView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.sets import RedisObject
        from suites.sets import SuiteTeaser

        if not self.suite.is_editor(request.user.pk) or request.user == request.user.is_moderator:
            raise Http404

        redis = RedisObject().get_redis_connection(slave=False)
        pipe = redis.pipeline()
        redis.pipeline(SuiteTeaser(self.suite.pk).clear())
        pipe.execute()

        return HttpResponse('ok')


class SuiteFetchTeaser(AjaxableResponseMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.suite_id = kwargs.get('pk', None)
        return super(SuiteFetchTeaser, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        from lib.utils import get_serialized_list
        if not self.suite_id:
            raise Http404

        return self.render_to_json_response({
            "object": get_serialized_list(request, [self.suite_id], 'suite:mini')[0]
        })

class SuiteAddSomethingView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        self.suite = get_object_from_pk(Suite, kwargs.get('pk', None), False)
        return super(SuiteAddSomethingView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        ''' first try to fetch stories or links; 
            if no results, try to match either the hash or (for Link objects) the link;
            if no results, does the string look like a link?
            if so, return a "fetch it" CTA '''
        from articles.api import StoryMiniResource
        from links.api import LinkMiniResource
        from links.utils import get_object_from_input
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.query = str(self.request.GET.get('q', ''))

        if self.query.find('?') > 0:
            self.query = self.query[:self.query.find('?')] # remove querystrings

        self.named_filter = str(self.request.GET.get('filter', ''))

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
        pks = None
        results = []

        if not self.suite:
            return Http404

        if self.query:
            from haystack.query import SearchQuerySet
            try:
                raw_results = SearchQuerySet().models(Link, Article).auto_query(self.query)[self.start:self.end]
            except Exception as e:
                pass            
            results = []
            try:
                if raw_results:
                    for thing in reversed(raw_results):
                        thing_object = None
                        if thing.model_name == 'link':
                            # TODO: adapt get_serialized_list to multi-model requests
                            thing_object = get_serialized_list(request, [thing.pk],'link:mini')
                        elif thing.model_name == 'article':
                            thing_object = get_serialized_list(request, [thing.pk],'story:mini')
                        if not thing_object:
                            continue
                        results.append(thing_object[0])
            except:
                pass

            if not results:
                external_fetch = get_object_from_input(request, self.query)
                if external_fetch:
                    if ContentType.objects.get_for_model(external_fetch) == ContentType.objects.get_for_model(Link):
                        results.append(api_serialize_resource_obj(external_fetch, LinkMiniResource(), request))
                    elif ContentType.objects.get_for_model(external_fetch) == ContentType.objects.get_for_model(Article):
                        results.append(api_serialize_resource_obj(external_fetch, StoryMiniResource(), request))

            if results:
                active_suite_posts = SuitePost.objects.filter(suite=self.suite).values_list('content_type__model', 'object_id')
                for r in results:
                    try:
                        if (str(r['ctype']), int(r['id'])) in active_suite_posts:
                            r['active'] = True
                    except Exception as e:
                        print(e)

            return self.render_to_json_response({
                    "objects": results
                }) 

        else:
            return HttpResponse(None)

    def post(self, request, *args, **kwargs):
        ''' post add/remove requests, external link fetches '''
        import json
        from articles.models import Article
        from suites.models import Suite
        from links.models import Link
        from suites.tasks import fanout_add_to_suite
        self.obj = None
        active = False

        # the thing we're adding
        content_id = request.POST.get('contentid', '')
        content_type = request.POST.get('contenttype', '')

        # todo:
        # > active list of SuitePost objects for this Suite
        # > is this thing in already? if so, remove

        if not content_id or not content_type:
            raise Http404

        if content_type == "story":
            self.obj = get_object_from_pk(Article, content_id, False)
        elif content_type == "link":
            self.obj = get_object_from_pk(Link, content_id, False)

        if not self.obj:
            raise Http404

        suite_posts = SuitePost.objects.filter(suite=self.suite, content_type=ContentType.objects.get_for_model(self.obj), object_id=self.obj.pk)
        if suite_posts:
            for sp in suite_posts:
                sp.invalidate()
                sp.delete()
            active = False

        else:
            suite_post, created = SuitePost.objects.get_or_create(suite=self.suite, content_type=ContentType.objects.get_for_model(self.obj), object_id=self.obj.pk)    
            if created:
                suite_post.added_by = request.user
                suite_post.save()
                suite_post.suite.invalidate()
                active = True
            fanout_add_to_suite(suite_post)
        return self.render_to_json_response(active)

class SuitesSelectorView(AjaxableResponseMixin, View):

    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(SuitesSelectorView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        content_id = request.GET.get('cid', '')
        content_type = request.GET.get('type', '')
        selected_on_client = request.POST.get('addlist', '')

        page = int(request.GET.get('page', '1'))
        querystring = str(request.GET.get('q', ''))

        if page:
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE

        active = []
        create = True if not content_type or not content_id else False

        if create:
            templist_string = request.POST.get('templist', unicode)
            if templist_string:
                active_unformatted = templist_string.split(',')
                if active_unformatted:
                    active = map(int, active_unformatted) # each as an int
                    
        else:
            if content_type == 'story':
                post = get_object_from_pk(Article, content_id, False)    
            elif content_type == 'link':
                post = get_object_from_pk(Link, content_id, False)    

            if post:      
                active = post.get_suite_pks(request, fetch_all=True)
                if selected_on_client:
                    active.append(selected_on_client)

        my_suites = request.user.get_my_suites(request, show_all=True)                 
        if my_suites:
            active_ordered = [s for s in my_suites if s['id'] in active]
            my_suites = [s for s in my_suites if not s['id'] in active]

            if active_ordered:
                for active in active_ordered:
                    active['active'] = True
                my_suites = active_ordered + my_suites

        return self.render_to_json_response({
            "objects": my_suites[start:end]
        })

    def post(self, request, *args, **kwargs):
        import json
        from articles.models import Article
        from suites.models import Suite
        from links.models import Link
        from articles.api import StoryMiniResource
        from links.api import LinkMiniResource        
        content_id = post = api_resource = None

        toggle_selected = True if request.POST.get('toggle', '') == 'true' else False
        initial_context = True if not toggle_selected else False
        selected_on_client = request.POST.get('addlist', '')

        content_type = request.POST.get('contenttype', 'story')
        content_id = request.POST.get('contentid', '')

        if not content_type or not content_id:
            raise Http404

        if content_type == "story":
            content_obj = get_object_from_pk(Article, content_id, False)
            api_resource = StoryMiniResource()
        elif content_type == "link":
            content_obj = get_object_from_pk(Link, content_id, False)
            api_resource = LinkMiniResource()

        if initial_context:
            if not content_obj:
                raise Http404            
            return self.render_to_json_response({
                'addObject': api_serialize_resource_obj(content_obj, api_resource, request)
            })            
            
        if toggle_selected:
            ''' add or remove current object (link or story) from suites 
                -- ie create or remove suitepost objects for the current
                content object '''            
            from suites.tasks import fanout_add_to_suite
            
            redis = RedisObject().get_redis_connection(slave=False)
            pipe = redis.pipeline()   

            suite_id = request.POST.get('suiteid', '')
            if not suite_id:
                raise Http404

            suite = get_object_from_pk(Suite, suite_id, False)
            if not suite:
                raise Http404

            active_suites = content_obj.get_suite_pks(request, fetch_all=True)
            if suite.pk in active_suites:
                suite_posts = SuitePost.objects.filter(suite=suite, content_type=ContentType.objects.get_for_model(content_obj), object_id=content_obj.pk)
                if suite_posts:
                    for sp in suite_posts:
                        sp.invalidate()
                        sp.delete()
            else:
                suite_post, created = SuitePost.objects.get_or_create(suite=suite, content_type=ContentType.objects.get_for_model(content_obj), object_id=content_obj.pk)    
                if created:
                    suite_post.added_by = request.user
                    suite_post.save()
                    suite.save()
                fanout_add_to_suite(suite_post)
            return HttpResponse('ok')