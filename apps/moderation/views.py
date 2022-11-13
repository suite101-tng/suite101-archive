import datetime, json, operator
from dateutil.relativedelta import relativedelta
from django.views.generic import TemplateView, View
from django.views.generic.edit import UpdateView
from django.views.generic import CreateView, FormView
from django.views.generic.list import ListView
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, HttpResponseNotFound
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from moderation.forms import FlagCreateForm
from django.db.models import Q, CharField, Value as V
from django.db.models.functions import Concat
import csv
from io import StringIO
from django.core.mail import EmailMessage   
from django.contrib.auth import get_user_model
from django.template.defaultfilters import *
from lib.utils import queryset_iterator, get_serialized_list

from articles.templatetags.bleach_filter import bleach_filter
from articles.models import Article
from links.models import Link, LinkProvider
from suites.models import Suite
from lib.mixins import AjaxableResponseMixin
from lib.decorators import ajax_login_required
from lib.enums import *
from lib.cache import get_object_from_pk
from lib.utils import get_serialized_list, api_serialize_resource_obj, suite_render
from profiles.api import UserMiniResource
from articles.api import StoryMiniResource
from suites.api import SuiteMiniResource
from .models import Flag, ModTags, ModNotes
from .sets import *

class ModCardView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, request, *args, **kwargs):
        return super(ModCardView, self).dispatch(request, *args, **kwargs)

    def clean(self, tag):
        tag = tag.replace(' ', '-')
        return tag

    def post(self, request, *args, **kwargs):
        from lib.tasks import user_index_check
        import time
        User = get_user_model()

        feature_toggle = request.POST.get("ftoggle", "")
        ads_toggle = request.POST.get("adstoggle", "")
        update_tags = True if request.POST.get("updatetags") == 'true' else False
        post_mod_note = True if request.POST.get("modnote") == 'true' else False
        toggle_approved = True if request.POST.get("toggleapproved") == 'true' else False
        
        content_type = request.POST.get("contenttype", "")
        content_id = request.POST.get("contentid", "")

        mod_card_data = {}

        if ads_toggle:
            content_pk = request.POST.get("cid", "")
            content_type = request.POST.get("ctype", "")

            story = get_object_from_pk(Article, content_pk)
            if not story:
                raise Http404

            if story.ads_override=='auto':
                story.ads_override = 'show'
            elif story.ads_override=='show':
                story.ads_override = 'hide'                
            else:
                story.ads_override = 'auto'
            story.save()
            story.invalidate()
            response = {'autoStatus': story.show_ads(), '%s' % story.ads_override: True }            

            return self.render_to_json_response(response)

        if feature_toggle:
            from moderation.tasks import clear_featured

            content_pk = request.POST.get("cid", "")
            content_type = request.POST.get("ctype", "")

            if not content_pk and content_type:
                raise Http404

            if content_type == "story":    
                model_type = Article
            elif content_type == "suite":
                model_type = Suite
            elif content_type == "user":
                model_type = User
            content = get_object_from_pk(model_type, content_pk)

            if not content:
                raise Http404

            content.featured = None if content.featured else datetime.datetime.now()
            content.save()
            content.invalidate()     
            clear_featured(content_type)

            return self.render_to_json_response(True if content.featured else False) 

        if content_type == 'story':
            try:
                obj = get_object_from_pk(Article, content_id)
                self.user = obj.author
                mod_card_data['object'] = api_serialize_resource_obj(obj, StoryMiniResource(), request)
                mod_card_data['user'] = api_serialize_resource_obj(self.user, UserMiniResource(), request)

                mod_card_data['object']['adsOn'] = (obj.ads_override == 'show')
                mod_card_data['object']['adsOff'] = (obj.ads_override == 'hide')
                mod_card_data['object']['adsAuto'] = (obj.ads_override == 'auto')
                mod_card_data['object']['adsEnabled'] = obj.show_ads()

                mod_card_data['storyType'] = True
            except:
                raise Http404

        elif content_type == 'suite':
            try:
                obj = get_object_from_pk(Suite, content_id)
                self.user = obj.owner
                mod_card_data['object'] = api_serialize_resource_obj(obj, SuiteMiniResource(), request)
                mod_card_data['user'] = api_serialize_resource_obj(self.user, UserMiniResource(), request)
                mod_card_data['suiteType'] = True
            except:
                raise Http404

        elif content_type == 'user':
            try:
                self.user = get_object_from_pk(User, content_id)
                mod_card_data['user'] = api_serialize_resource_obj(self.user, UserMiniResource(), request)
                mod_card_data['userType'] = True
            except:
                raise Http404

        elif post_mod_note:
            content_object = None
            note_type = request.POST.get("notetype", "")                    
            content_id = request.POST.get("cid", "")
            if note_type == 'user':
                content_object = get_object_from_pk(User, content_id)

            # elif content_id == 'story':
            #     content_object = get_object_from_pk(Article, content_id)
            # elif content_id == 'suite':
            #     content_object = get_object_from_pk(Suite, content_id)

            moderator = request.user
            message = request.POST.get("msg", "")

            if not message or not moderator or not content_object:
                return self.render_to_json_response(False)                

            mod_note = ModNotes.objects.create(content_type=ContentType.objects.get_for_model(content_object), object_id=content_object.pk, moderator=moderator, message=message)
            mod_note.fanout_notification()
            
            if not mod_note:
                raise Http404

            return self.render_to_json_response([mod_note.serialize()]) 

        elif update_tags:
            tagged_user_pk = request.POST.get("userid", "")
            tagged_user = get_object_from_pk(User, tagged_user_pk)
            tag_list = request.POST.get("tags", "")
            mod_tags, created = ModTags.objects.get_or_create(user=tagged_user)
            mod_tags.tag_list = tag_list
            mod_tags.save();
            tags_formatted = json.loads(str(mod_tags.tag_list))
            objects = [{'tag': '%s' % tag, 'tagUrl': '/admin/tags?q=%s' % self.clean(tag)} for tag in tags_formatted]
            return self.render_to_json_response({
                "objects": objects
            })

        elif toggle_approved:
            from lib.tasks import user_index_check
            user_pk = request.POST.get("userid", "")
            user = get_object_from_pk(User, user_pk)            

            if user.approved:
                user.approved = False
            else:
                user.approved = True

            user.invalidate()
            user.save()

            user_index_check(user)
            user.invalidate()
            return self.render_to_json_response(user.approved)

        mod_card_data['user']['approved'] = self.user.approved
        mod_card_data['user']['lastSeen'] =  time.mktime(self.user.seen().timetuple())
        mod_card_data['user']['dateJoined'] =  time.mktime(self.user.date_joined.timetuple())
        
        mod_card_data['user']['stats'] = self.user.get_user_stats()
        mod_card_data['user']['modNotes'] = self.user.get_mod_notes()

        try:
            mod_card_data['object']['featured'] = True if obj.featured or obj.featured_on else False
        except:
            pass
        
        try:
            mod_tags = ModTags.objects.get(user=self.user)
            tag_list = json.loads(str(mod_tags.tag_list))
            mod_card_data['modTags'] = [{'tag': '%s' % tag, 'tagUrl': '/admin/tags?q=%s' % self.clean(tag)} for tag in tag_list]

        except Exception as e:
            mod_card_data['modTags'] = []

        return self.render_to_json_response(mod_card_data)            


class ModDeleteSpammyView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, request, *args, **kwargs):
        User = get_user_model()
        self.user = get_object_from_pk(User, int(request.POST.get("userid", ""))  )
        return super(ModDeleteSpammyView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.tasks import user_index_check
        from profiles.sets import UserTeaser
        
        if not self.user:
            raise Http404

        try:
            UserTeaser(self.user.pk).clear()
            self.user.delete()
        except Exception as e:
            print(e)

        return HttpResponse('ok')

class ModFlagStatsFetch(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, *args, **kwargs):
        return super(ModFlagStatsFetch, self).dispatch(*args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        User = get_user_model()
        from moderation.models import Flag, RoyalApplication
        
        story_flags = Flag.objects.all().filter(cleared=False, content_type=ContentType.objects.get_for_model(Article)).count()
        suite_flags = Flag.objects.all().filter(cleared=False, content_type=ContentType.objects.get_for_model(Suite)).count()
        user_flags = Flag.objects.all().filter(cleared=False, content_type=ContentType.objects.get_for_model(User)).count()
        discussion_flags = Flag.objects.all().filter(cleared=False, content_type=ContentType.objects.get_for_model(Chat)).count()

        response = {
            'stories': story_flags,
            'suites': suite_flags,
            'users': user_flags,
            'discussions': discussion_flags
        }

        return self.render_to_json_response(response)

class ArticleDeferView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, *args, **kwargs):
        return super(ArticleDeferView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        article_pk = kwargs.get('pk', None)
        if not article_pk:
            raise Http404

        article = get_object_from_pk(Article, article_pk)
        if article.deferred:
            article.deferred = False
        else:
            article.deferred = True
        article.save()
        article.invalidate()

        return HttpResponse('ok')
  

class ModFlagView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ModFlagView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        User = get_user_model()
        from moderation.models import Flag
        from stats.tasks import process_local_stats_event
        from lib.sets import RedisObject
        import json

        # redis = RedisObject().get_redis_connection(slave=False)
        # pipe = redis.pipeline()

        flag_content_pk = request.POST.get("flagcontentid", "")
        content_type = request.POST.get("contenttype", "")
        flag_message = request.POST.get("message", "")
        flag_reason = request.POST.get("reason", "")
        
        if content_type == "user":
            flagged_object = get_object_from_pk(User, flag_content_pk, False)
            flagged_type = ContentType.objects.get_for_model(User)

        flag = Flag.objects.create(content_type=flagged_type, content_object=flagged_object, object_id=flag_content_pk, message=flag_message, user=self.request.user, reason=flag_reason)
        
        return HttpResponse('ok')
        

class ModClearFlagView(AjaxableResponseMixin, View):

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, request, *args, **kwargs):
        return super(ModClearFlagView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        import time
        from django.http import HttpResponse
        from moderation.models import Flag

        flag_pk = request.POST.get("flagid", "")
        if not flag_pk:
            raise Http404

        flag = get_object_from_pk(Flag, flag_pk, False)
        flag.cleared = True
        flag.save()

        return HttpResponse('ok')


class GetModFlagListView(AjaxableResponseMixin, View):

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, request, *args, **kwargs):
        return super(GetModFlagListView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        User = get_user_model()
        import time
        from django.http import HttpResponse
        from moderation.models import Flag

        objects = []

        flags = Flag.objects.active()

        for flag in flags:
            flag_item = {}

            flag_object = flag.content_object
            try:
                flag_object_pk = flag.content_object.pk
            except:
                # object does not exsit; kill the flag
                flag.delete()
                pass
                            
            flag_item['created'] = time.mktime(flag.created.timetuple())
            
            flag_item['userName'] = flag.user.get_full_name()
            flag_item['userId'] = flag.user.pk
            flag_item['userUrl'] = flag.user.get_absolute_url()
            flag_item['userImg'] = flag.user.get_profile_image()   

            try:
                flag_item['objUrl'] = flag.content_object.get_absolute_url()
            except:
                pass

            if flag.content_type == ContentType.objects.get_for_model(User):
                flag_item['userFlag'] = True
                flag_item['objName'] = flag.content_object.get_full_name()

            flag_item['id'] = flag.pk
            flag_item['message'] = flag.message
            if flag.reason:
                flag_item['reason'] = flag.reason
            
            objects.append(flag_item)

        return self.render_to_json_response({
                "objects": objects
            })


class AdminMonitorView(AjaxableResponseMixin, TemplateView):
    template_name = 'admin/admin_monitor_detail.html'
    admin_type = None

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: u.is_moderator))
    def dispatch(self, request, *args, **kwargs):
        self.admin_type = kwargs.get('admin_type')
        return super(AdminMonitorView, self).dispatch(request, *args, **kwargs)

    def get_current_featured_tags():
        return ['test', 'testing', 'atest']

    def post(self, request, *args, **kwargs):
        update_provider = True if request.POST.get("updateprovider", "") == 'true' else False

        if update_provider:
            try:
                provider_name = request.POST.get("name", "")
                provider_link = request.POST.get("url", "")
                provider_pk = request.POST.get("providerid", "")
                provider_image_pk = request.POST.get("providerimg", "")
                provider = LinkProvider.objects.get(pk=provider_pk)
            except:
                return Http404

            if provider_image_pk:
                from links.models import LinkProviderImage
                try:
                    provider_image = LinkProviderImage.objects.get(pk=provider_image_pk)
                    if provider_image:
                        provider.image = provider_image
                except Exception as e:
                    print('problem getting provider image object: %s' % e)
            provider.name = provider_name
            provider.link = provider_link
            provider.save()
            provider.invalidate()

        if self.admin_type == "toggle_tag":        
            selected_tag = request.POST.get("selected", "")
            if not selected_tag:
                raise Http404

            if selected_tag in self.get_current_featured_tags():
                # remove from featuerd set
                featured_status = False
                return
            else:
                # add to featured set
                featured_status = True
            return self.render_to_json_response({
                "status": featured_status
            })

        return HttpResponse('ok')

    def get(self, request, *args, **kwargs):
        User = get_user_model()
        from stats.sets import StatsFailedEventList
        self.feed = [];
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.query = str(self.request.GET.get('q', ''))
        self.named_filter = str(self.request.GET.get('filter', ''))

        if not self.admin_type:
            self.admin_type = 'home'

        try:
            self.page_num = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page_num = 1

        # Note: we unsafely assume has_next if len(results) == DEFAULT_PAGE_SIZE; improve this later
        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False         

        if self.admin_type == 'home':
            self.failed_events = StatsFailedEventList().get_list()

        elif self.admin_type == 'links':
            link_pks = Link.objects.all().values_list('pk', flat=True)[self.start:self.end]
            if link_pks:
                self.feed = get_serialized_list(request, link_pks,'link:mini')[:DEFAULT_PAGE_SIZE]

        elif self.admin_type == 'stories':
            if self.query:
                split_querystring = self.query.split('-')
                query = reduce(operator.and_, (Q(title__icontains=x) for x in split_querystring))

                if self.named_filter=="noob":
                    pks = Article.objects.published().filter(author__approved=False, author__is_active=True).exclude(deferred=True).filter(query).values_list('pk', flat=True)[self.start:self.end]
                elif self.named_filter=="deferred":
                    pks = Article.objects.published().filter(author__approved=False, author__is_active=True, deferred=True).filter(query).values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = Article.objects.published().filter(author__approved=True, author__is_active=True).filter(query).values_list('pk', flat=True)[self.start:self.end]

            else:
                if self.named_filter=="noob":
                    pks = Article.objects.published().filter(author__approved=False, author__is_active=True).exclude(deferred=True).values_list('pk', flat=True)[self.start:self.end]
                elif self.named_filter=="deferred":
                    pks = Article.objects.published().filter(author__approved=False, author__is_active=True, deferred=True).values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = Article.objects.published().filter(author__approved=True, author__is_active=True).values_list('pk', flat=True)[self.start:self.end]

            if pks: 
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(self.request, pks,'story:mini')[:DEFAULT_PAGE_SIZE]

        elif self.admin_type == 'suites':
            if self.query:
                split_querystring = self.query.split('-')
                query = reduce(operator.and_, (Q(name__icontains=x) for x in split_querystring))
                pks = Suite.objects.filter(owner__is_active=True).filter(query).values_list('pk', flat=True)[self.start:self.end]

            else:
                pks = Suite.objects.filter(owner__is_active=True).values_list('pk', flat=True)[self.start:self.end]

            if pks: 
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(self.request, pks,'suite:mini')[:DEFAULT_PAGE_SIZE]

        elif self.admin_type == 'members':
            if self.query:
                split_querystring = self.query.split('-')
                query = reduce(operator.and_, (Q(full_name__icontains=x) for x in split_querystring))

                if self.named_filter=="new":
                    pks = User.objects.annotate(full_name=Concat('first_name', V(' '), 'last_name')).filter(approved=False, is_active=True).filter(query).values_list('pk', flat=True)[self.start:self.end]
                elif self.named_filter=="legs":
                    pks = User.objects.annotate(full_name=Concat('first_name', V(' '), 'last_name')).filter(legacy_user_id__isnull=False).filter(query).values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = User.objects.annotate(full_name=Concat('first_name', V(' '), 'last_name')).filter(is_active=True, last_pub_date__isnull=False).filter(query).values_list('pk', flat=True).order_by('-last_pub_date')[self.start:self.end]

            else:
                if self.named_filter=="new":
                    pks = User.objects.filter(approved=False, is_active=True).values_list('pk', flat=True)[self.start:self.end]                
                elif self.named_filter=="legs":
                    pks = User.objects.filter(legacy_user_id__isnull=False).values_list('pk', flat=True).order_by('-pk')[self.start:self.end]                    
                else:
                    pks = User.objects.filter(is_active=True, last_pub_date__isnull=False).values_list('pk', flat=True).order_by('-last_pub_date')[self.start:self.end]

            if pks: 
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                objects = get_serialized_list(self.request, pks,'user:mini')[:DEFAULT_PAGE_SIZE]

                for obj in objects:
                    try:
                        mod_tags = ModTags.objects.get(user__pk=obj['id'])
                        tag_list = json.loads(str(mod_tags.tag_list))
                        obj['modTags'] = [{'tag': '%s' % tag, 'tagUrl': '/admin/tags?q=%s' % tag.replace(' ', '-')} for tag in tag_list]
                    except Exception as e:
                        pass

                self.feed = objects

        elif self.admin_type == 'flags':
            if self.query:
                split_querystring = self.query.split('-')
                query = reduce(operator.and_, (Q(name__icontains=x) for x in split_querystring))
                if self.named_filter=="cleared":
                    pks = Flag.objects.filter(cleared=True).filter(query).values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = Flag.objects.filter(cleared=False).filter(query).values_list('pk', flat=True)[self.start:self.end]

            else:
                if self.named_filter=="cleared":
                    pks = Flag.objects.filter(cleared=True).values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = Flag.objects.filter(cleared=False).values_list('pk', flat=True)[self.start:self.end]

            if pks: 
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(self.request, pks,'flag:mini')[:DEFAULT_PAGE_SIZE]

        elif self.admin_type == "tags":
            # get popular tags
            # get current featured list
            # if tag in current featured list, mark 'featured'
            # return featured and popular/all[:50] tags 
            self.feed = None


        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                    "objects": self.feed
                })

        return super(AdminMonitorView, self).get(request, *args, **kwargs)

    def get_inner_context(self):
        innercontext = {}
        innercontext['adminType'] = self.admin_type
        innercontext['currentUrl'] = self.request.get_full_path().split('?')[0]
        innercontext['namedFilter'] = self.named_filter         

        if self.page_num > 1:
            innercontext['currentPage'] = self.page_num     
        
        if self.admin_type == "home":
            innercontext['title'] = 'Suite admin'
            innercontext['adminHome'] = True

        elif self.admin_type == "stories":
            innercontext['title'] = 'Stories admin'
            innercontext['storiesType'] = True

        elif self.admin_type == "links":
            innercontext['title'] = 'Links admin'
            innercontext['linksType'] = True

        elif self.admin_type == "flags":
            innercontext['title'] = 'Flags admin'
            innercontext['flagsType'] = True

        elif self.admin_type == "suites":
            innercontext['title'] = 'Suites admin'
            innercontext['suitesType'] = True

        elif self.admin_type == "tags":
            innercontext['title'] = 'Tags admin'
            innercontext['tagsAdmin'] = True
        
        elif self.admin_type == "members":
            innercontext['title'] = 'Members admin'
            innercontext['membersType'] = True

        return innercontext

    def get_context_data(self, **kwargs):
        context = super(AdminMonitorView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()

        context['admin_type'] = self.admin_type
        context['admin_rendered'] = suite_render(self.request, 'admin-monitor', innercontext, False)
        return context






