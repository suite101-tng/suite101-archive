import os
import logging
import datetime
import json
import collections
from random import randint, randrange
log = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.template import loader, Context
from django.views.generic import CreateView
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import patch_cache_control
from django.contrib.auth.decorators import user_passes_test

from project import settings
from suites.models import Suite
from articles.models import Article
from conversations.models import Conversation, Post 
from lib.enums import *
from lib.decorators import ajax_login_required
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.models import Follow
from lib.cache import get_object_from_hash, get_object_from_pk, get_object_from_slug
from lib.utils import api_serialize_resource_obj, suite_render, get_serialized_list
from articles.api import StoryMiniResource
from profiles.forms import UserCreateForm
from profiles.api import UserMiniResource

def nginx_status(request):
    """ read the env variable and return based on what our status is """
    status = os.environ.get('SERVER_STATUS', '1')
    if status == '1':
        return HttpResponse('ok')
    raise Http404     

class GenericFollowView(View):
    @method_decorator(ajax_login_required)
    def dispatch(self, *args, **kwargs):
        self.model_object = kwargs.get('model_object')
        self.content_type = ContentType.objects.get_for_model(self.model_object)
        return super(GenericFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        obj = get_object_from_pk(self.model_object, pk=pk)
        try:
            self.follow, created = Follow.objects.get_or_create(
                content_type=self.content_type,
                object_id=obj.pk,
                user=request.user
            )
        except:
            # cleanup duplicate follow objects
            try:
                Follow.objects.all().filter(
                    content_type=self.content_type,
                    object_id=obj.pk,
                    user=request.user
                )[0:].delete()
            except Exception as e:
                print(e)

        # save the object so we can use it to invalidate cache if needed
        self.obj = obj
        return HttpResponse('ok')


class GenericUnFollowView(View):
    @method_decorator(ajax_login_required)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.model_object = kwargs.get('model_object')
        self.content_type = ContentType.objects.get_for_model(self.model_object)
        return super(GenericUnFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        obj = get_object_from_pk(self.model_object, pk=pk)
        try:
            Follow.objects.all().filter(
                content_type=self.content_type,
                object_id=obj.pk,
                user=request.user
            ).delete()
        except Exception as e:
            pass

        # save the object so we can use it to invalidate cache if needed
        self.obj = obj
        return HttpResponse('ok')


def slug_matcher(request, slug, edit_mode=False, feed_type=None):
    from profiles.views import UserDetailView
    from lib.cache import get_object_from_hash
    try:
        obj = get_object_from_hash(slug, False)
    except:
        obj = None
    if obj:
        return HttpResponsePermanentRedirect(obj.get_absolute_url())

    return UserDetailView.as_view(slug=slug, feed_type=feed_type)(request)

def member_root_slug_matcher(request, hashed_id, author=None):
    from conversations.views import ConversationDetailView
    from lib.cache import get_object_from_hash
    try:
        obj = get_object_from_hash(hashed_id, False)
        
        return HttpResponsePermanentRedirect(obj.conversation.get_absolute_url())
        
        
        # return ConversationDetailView.as_view(conversation=obj)(request)
    except:
        raise Http404

def hash_decoder(request, hashed_id):
    from lib.utils import decode_hashed_id
    try:
        obj_type, obj_id = decode_hashed_id(hashed_id)
    except:
        obj_type = HASH_TYPE_UNKNOWN
        obj_id = None
    else:
        if not isinstance(obj_id, int):
            obj_type = HASH_TYPE_UNKNOWN
            obj_id = None
    data = json.dumps({
        'object_type': obj_type,
        'object_id': obj_id
    })
    response_kwargs = {}
    response_kwargs['content_type'] = 'application/json'
    return HttpResponse(data, **response_kwargs)

class TermsView(TemplateView):
    template_name = 'terms.html'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated() and not self.request.user.accepted_terms:
            self.request.user.accepted_terms = True
            self.request.user.save()
        return super(TermsView, self).dispatch(*args, **kwargs)


class RulesView(TemplateView):
    template_name = 'rules.html'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated() and not self.request.user.read_rules:
            self.request.user.read_rules = True
            self.request.user.invalidate()
            self.request.user.save()
        return super(RulesView, self).dispatch(*args, **kwargs)

class ArchiveView(TemplateView, AjaxableResponseMixin):
    template_name = 'static/static_detail.html'
    static_type = 'archived'

    @method_decorator(ajax_login_required)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ArchiveView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        innercontext = self.get_inner_context()
        return self.render_to_json_response(innercontext)

    def get_inner_context(self):
        innercontext = {}
        innercontext['viewType'] = 'archived'
        # innercontext['articles'] = self.articles

        return innercontext

    def get(self, request, *args, **kwargs):
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
        self.questions = pks = []
        results = []
        is_mod = True if request.user.is_authenticated() and request.user and request.user.is_moderator else False
                    
        self.articles = request.user.get_user_stories(request)

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                    "objects": self.articles
                }) 

        return super(ArchiveView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ArchiveView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()
        context['view_type'] = 'archived'
        context['static_rendered'] = suite_render(self.request, 'archive-shell', innercontext, False)
        return context

class StaticView(TemplateView, AjaxableResponseMixin):
    template_name = 'static/static_detail.html'
    static_type = error_type = None

    def dispatch(self, *args, **kwargs):
        self.view_type = self.static_type
        return super(StaticView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.content = self.get_static_content()
        if not self.content:
            raise Http404
        innercontext = self.get_inner_context()
        return self.render_to_json_response(innercontext)

    def get_static_content(self):
        if self.view_type == 'error':
            content_filename = 'errors/_%s.html' % self.error_type   
        else:
            content_filename = '_%s.html' % self.view_type   

        content_file = open(os.path.join(settings.PROJECT_ROOT, 'templates/static/%s' % content_filename), 'r+')
        self.content = str(content_file.read())
        content_file.close()    
        return self.content

    def get_inner_context(self):
        innercontext = {}
        innercontext['viewType'] = self.view_type        

        if self.view_type == 'about':
            innercontext['featuredSuite'] =  self.featured_suite
            innercontext['promoStories'] = self.featured_conversation
        else:
            innercontext['content'] = self.content
        return innercontext

    def get(self, request, *args, **kwargs):
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        nocontext = ['notfound']
        if self.view_type in nocontext:
            self.content = None

        if self.view_type == 'about':
            from django.db import models
            from lib.utils import get_featured_suites, get_discussed_stories, get_recommended_stories
            from suites.models import Suite
            from articles.models import StoryParent
            from suites.api import SuiteMiniResource
            from lib.sets import RedisObject, PromoConversations

            redis = RedisObject().get_redis_connection()
            pipe = redis.pipeline()            
            
            suite_pks = get_featured_suites()[:50]
            if suite_pks:
                max_range = len(suite_pks) - 1
                index = randint(0,max_range)
                suite = get_object_from_pk(Suite, suite_pks[index], False)
                self.featured_suite = api_serialize_resource_obj(suite, SuiteMiniResource(), request)

            promo_stories = PromoConversations().get_full_set()
            if not promo_stories:
                candidates = []
                recommended_pks = get_recommended_stories()
                stories_with_responses = StoryParent.objects.filter(story__status='published', content_type=ContentType.objects.get_for_model(Article), object_id__in=list(recommended_pks)).values('object_id').annotate(responses=models.Count('story__pk'))
                for story_tuple in stories_with_responses:
                    if story_tuple['responses'] > 2:
                        candidates.append(story_tuple['object_id'])

                if candidates:
                    max_range = len(candidates) - 1
                    index = randint(0,max_range)
                    promo_parent = candidates[index]
                    promo_stories = [promo_parent]
                    redis.pipeline(PromoConversations().add_to_set(promo_parent, 0))
                    parent_objects = StoryParent.objects.filter(story__status='published', object_id=promo_parent, story__author__is_active=True)                    
                    for p in parent_objects:
                        promo_stories.append(p.story.pk)
                        redis.pipeline(PromoConversations().add_to_set(p.story.pk, 1))
                    redis.pipeline(PromoConversations().expire(settings.DEFAULT_CACHE_TIMEOUT))
                    pipe.execute()

            self.featured_conversation = get_serialized_list(request, promo_stories,'story:mini')

        else:
            self.content = self.get_static_content()
            if not self.content:
                raise Http404        

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        return super(StaticView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StaticView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()
        context['view_type'] = self.view_type

        if self.view_type == "about":
            template = 'static-about'
        else:
            template = 'static-shell'
        context['static_rendered'] = suite_render(self.request, template, innercontext, False)
        return context

class FetchTrendingTags(AjaxableResponseMixin, View):
    def dispatch(self, *args, **kwargs):
        return super(FetchTrendingTags, self).dispatch(*args, **kwargs)

    def clean(self, tag):
        tag = tag.replace(' ', '-')
        return tag

    def post(self, request, *args, **kwargs):
        from django.db.models import Q
        from lib.utils import get_top_tags

        max_tags = request.POST.get('please') or 5
        tags = get_top_tags()
        if not tags:
            return self.render_to_json_response({
                "error": True
            })
        response = [{'tag': '%s' % tag, 'tagUrl': '/q/%s' % self.clean(tag)} for tag in tags]
        return self.render_to_json_response({
            "objects": response
        })

class SearchView(AjaxableResponseMixin, View):

    def dispatch(self, *args, **kwargs):
        response = super(SearchView, self).dispatch(*args, **kwargs)
        return response

    def next_in_array(self, array):
        try:
            return True if len(array) > DEFAULT_PAGE_SIZE else False
        except:
            return False

    def get(self, request, *args, **kwargs):
        from suites.api import SuiteSearchResource
        from articles.api import StorySearchResource
        from profiles.api import UserSearchResource

        self.query = kwargs.get('query', '').replace('-', ' ')
        self.filter_type = request.GET.get('filter', '') or ''
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.search_results = []

        def get_query_data(query_type, start, end):
            if query_type == 'stories':
                search_resource = StorySearchResource()
            elif query_type == 'suites':
                search_resource = SuiteSearchResource()
            elif query_type == 'users':
                search_resource = UserSearchResource()
            results = search_resource.do_search(request, query=self.query, start=start, end=end)

            if results:
                ''' try to fetch related tags - the most commonly used tags from these results'''
                related_tags = []
                for result in results:
                    try:
                        tags = result['tags']
                        try:
                            if int(result['authorIndex']) > 1:
                                # double-weight tags used by highly rated members
                                tags += tags
                        except:
                            pass
                        related_tags += tags
                    except:
                        pass
                collected_tags=collections.Counter(related_tags)
                self.related_tags = ([item for item,count in collected_tags.most_common(5)])
            return results

        self.search_results = {}
        try:
            self.page_num = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page_num = 1

        # Note: we unsafely assume has_next if len(results) == DEFAULT_PAGE_SIZE; improve this later
        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False         

        if not self.filter_type:
            stories = get_query_data('stories', start=0, end=3)
            if stories:
                self.search_results['stories'] = stories[:2]
                if len(stories) == 3:
                    self.search_results['moreStories'] = True
            suites = get_query_data('suites', start=0, end=3)
            if suites:
                self.search_results['suites'] = suites[:2]
                if len(suites) == 3:
                    self.search_results['moreSuites'] = True                
            users = get_query_data('users', start=0, end=3)
            if users:
                self.search_results['users'] = users[:2]
                if len(users) == 3:
                    self.search_results['moreUsers'] = True
            if not users and not stories and not suites:
                self.search_results['noResults'] = True

            return self.render_to_json_response(self.search_results)

        elif self.filter_type == "stories":     
            self.search_results = get_query_data('stories', start=self.start, end=self.end)
            self.has_next = self.next_in_array(self.search_results)

        elif self.filter_type == "suites":               
            self.search_results = get_query_data('suites', start=self.start, end=self.end)
            self.has_next = self.next_in_array(self.search_results)

        elif self.filter_type == "people": # we want to call 'em people, not users, on the outside              
            self.search_results = get_query_data('users', start=self.start, end=self.end)
            self.has_next = self.next_in_array(self.search_results)
        
        return self.render_to_json_response({
                "objects": self.search_results
            })


class ExploreView(AjaxableResponseMixin, TemplateView):
    template_name = 'explore/explore_detail.html'

    def dispatch(self, *args, **kwargs):
        self.feed_type = kwargs.get('feed_type')
        response = super(ExploreView, self).dispatch(*args, **kwargs)
        return response

    def clean_tag(self, tag):
        tag = tag.replace(' ', '-')
        return tag 

    def get(self, request, *args, **kwargs):
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        self.current_tab = ''
        story_types = ['long', 'latest', 'top', 'discussed']
        suite_types = ['suites']
        user_types = ['people']

        if self.feed_type in story_types:
            self.current_tab = 'stories'
        elif self.feed_type in suite_types:
            self.current_tab = 'suites'
        elif self.feed_type in user_types:
            self.current_tab = 'people'

        override_feed_type = request.GET.get('viewtype', '')
        if override_feed_type:
            self.feed_type = override_feed_type
        try:
            self.page_num = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page_num = 1

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
        
        from articles.models import Article
        from django.template.loader import render_to_string
        from lib.utils import get_discussed_stories, get_top_stories, get_featured_suites
        pks = []
        self.feed = []

        if self.feed_type == "explore":  
            self.explore_suites = self.featured_members = self.explore_top_tags = []

            # latest stories
            latest_story_pks = Article.objects.published().filter(author__approved=True).values_list('pk', flat=True).order_by('-created')[self.start:self.end]
            if latest_story_pks:
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(request, latest_story_pks,'story:mini')[:DEFAULT_PAGE_SIZE]

            if not self.page_num > 1:
                # featured suites
                featured_suite_pks = get_featured_suites()[:6]
                if featured_suite_pks:
                    self.explore_suites = get_serialized_list(request, featured_suite_pks,'suite:mini')

                # trending tags
                from lib.utils import get_top_tags

                max_tags = 25
                tags = get_top_tags()
                if tags:
                    self.explore_top_tags = [{'tag': '%s' % tag, 'tagUrl': '/q/%s' % self.clean_tag(tag)} for tag in tags]      

                # featured members
                from lib.utils import get_featured_members
                featured_member_pks = get_featured_members()[:3]     
                if featured_member_pks:
                    self.featured_members = get_serialized_list(self.request, featured_member_pks[:DEFAULT_PAGE_SIZE],'user:mini')            

        if self.feed_type == "latest":               
            pks = Article.objects.published().filter(author__approved=True).values_list('pk', flat=True).order_by('-created')[self.start:self.end]
            if pks:
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(request, pks,'story:mini')[:DEFAULT_PAGE_SIZE]

        if self.feed_type == "long":               
            long_read = 1500

            if not request.user.is_authenticated():
                pks = Article.objects.published().filter(author__approved=True, word_count__gte=long_read).values_list('pk', flat=True).order_by('-created')[self.start:self.end]
            else:
                pks = Article.objects.published().filter(author__approved=True, word_count__gte=long_read).values_list('pk', flat=True).order_by('-created')[self.start:self.end]
            if pks:
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(request, pks,'story:mini')[:DEFAULT_PAGE_SIZE]                

        if self.feed_type == "top":
            pks = get_top_stories(7, self.page_num)
            if pks:
                self.feed = get_serialized_list(request, pks,'story:mini')

        if self.feed_type == "suites":
            pks = get_featured_suites()[self.start:self.end]
            if pks:
                self.explore_suites = get_serialized_list(request, pks,'suite:mini')

        if self.feed_type == "people":
            from lib.utils import get_featured_members
            pks = get_featured_members()[self.start:self.end]     
            if pks:
                self.feed = get_serialized_list(self.request, pks[:DEFAULT_PAGE_SIZE],'user:mini')

        if self.feed_type == "discussed":
            pks = get_discussed_stories(self.page_num)
            if pks:
                self.feed = get_serialized_list(request, pks,'story:mini')
        
        if pks:
            self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
        
        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                    "objects": self.feed
                })

        return super(ExploreView, self).get(request, args, kwargs)        

    def get_inner_context(self):
        innercontext = {}
        innercontext['userLoggedIn'] = self.request.user.is_authenticated()
        innercontext['currentUrl'] = self.request.get_full_path().split('?')[0]
        innercontext['currentTab'] = self.current_tab
        if self.has_next:
            innercontext['nextPage'] = self.page_num + 1
        if self.has_previous:       
            innercontext['prevPage'] = self.page_num - 1
        innercontext['exploreType'] = self.feed_type
        
        if self.page_num > 1:
            innercontext['currentPage'] = self.page_num     

        if self.feed_type == "explore":
            innercontext['explore'] = True
            innercontext['title'] = 'Explore'
            innercontext['latestStories'] = self.feed
            if not self.page_num > 1:
                innercontext['suites'] = self.explore_suites
                innercontext['topTags'] = self.explore_top_tags
                innercontext['exploreMembers'] = self.featured_members

        if self.feed_type == "people":
            innercontext['members'] = self.feed
            innercontext['userType'] = True
            innercontext['title'] = 'Featured contributors'
            innercontext['featuredMembers'] = True

        if self.feed_type == "suites":
            innercontext['suites'] = self.feed
            innercontext['suiteType'] = True
            innercontext['title'] = 'Featured Suites'

        if self.feed_type == "discussed":
            innercontext['discussedType'] = True
            innercontext['title'] = 'Actively discussed stories'
            innercontext['stories'] = self.feed
            innercontext['discussedStories'] = True

        if self.feed_type == "long": 
            innercontext['longType'] = True
            innercontext['stories'] = self.feed
            innercontext['title'] = 'Longer reads'
            innercontext['longReads'] = True

        if self.feed_type == "top": 
            innercontext['topType'] = True
            innercontext['stories'] = self.feed
            innercontext['title'] = 'Top stories today'
            innercontext['topStories'] = True

        if self.feed_type == "latest":
            innercontext['latestType'] = True
            innercontext['storyType'] = True            
            innercontext['stories'] = self.feed
            innercontext['title'] = 'Recent stories'

        return innercontext

    def get_context_data(self, **kwargs):
        from suites.api import SuiteSearchResource
        from articles.api import StorySearchResource
        from profiles.api import UserSearchResource
        from lib.utils import get_serialized_list

        context = super(ExploreView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()

        context['index_status'] = "index, follow"    
        if self.page_num > 1:
            context['canonical_link'] = self.request.get_full_path()
            context['index_status'] = "noindex, follow"              
        else:
            context['canonical_link'] = self.request.get_full_path().split('?')[0]

        context['page_num'] = self.page_num      

        if self.feed_type == "explore":
            context['title'] = 'Explore'
            context['description'] = 'Suites are collections of stories and collaborations between members. Flip through some of our most popular. '        

        if self.feed_type == "people":
            context['title'] = 'Featured contributors'
            context['description'] = 'Meet some of the top writers on Suite.'

        if self.feed_type == "discussed":
            context['title'] = 'Stories we\'re discussing'
            context['description'] = 'Actively discussed stories on Suite. '
        
        if self.feed_type == "top": 
            context['title'] = 'Top stories today'
            context['description'] = 'The most read stories on Suite.'

        if self.feed_type == "latest":
            context['title'] = 'Recent stories'
            context['description'] = "Recent stories from everyone."

        context['view_type'] = self.feed_type
        context['current_tab'] = self.current_tab
        context['explore_rendered'] = suite_render(self.request, 'explore-shell', innercontext, False)
        context['page_num'] = self.request.GET.get('page', '1')
        context['current_url'] = self.request.get_full_path().split('?')[0]
        context['explore_json_str'] = json.dumps(innercontext)
                
        return context



