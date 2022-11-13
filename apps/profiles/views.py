from __future__ import division
import json, operator, logging, datetime, time
from random import randint
from django import forms
from django.contrib.auth import get_user_model
from django.views.generic import CreateView
from django.views.generic.detail import DetailView
from functools import reduce
from django.views.generic.base import RedirectView, View
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import patch_cache_control
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.http import Http404, HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models import Q, CharField, Value as V
from django.db.models.functions import Concat

from lib.views import GenericFollowView, GenericUnFollowView
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.tasks import new_member
from lib.utils import send_reset_email, send_email_change_email, resize_profile_image, send_activation_email
from lib.utils import api_serialize_resource_obj, check_user_ip_ban, get_serialized_list
from lib.utils import get_client_ip, suite_render
from lib.enums import *
from lib.cache import  get_object_from_pk, get_object_from_slug
from articles.sets import UserMainStoryFeed
from profiles.sets import UserFollowersSet, UserFollowsUsersSet, UserFollowsSuitesSet
from suites.models import SuiteInvite
from articles.models import Article
from articles.api import StoryMiniResource
from suites.api import SuiteMiniResource
from stats.tasks import process_local_stats_event

from .forms import EmailAuthenticationForm, RequestResetPasswordForm, ResetPasswordForm, UserUpdateForm, UserCreateForm, UserTwitterRegistrationForm, TwitterLinkForm, ChangeEmailForm, UserUploadImageForm
from .models import UserBlackList, UserEmailSettings
from .api import UserResource

logger = logging.getLogger(__name__)


class UserCreateView(AjaxableResponseMixin, CreateView):
    model = get_user_model()
    form_class = UserCreateForm
    template_name = 'profiles/register.html'
    success_url = reverse_lazy('register_thanks')

    def dispatch(self, request, *args, **kwargs):
        if settings.LOGIN_DISABLED:
            self.template_name = 'profiles/no_login.html'
        else:
            if request.user.is_authenticated():
                return HttpResponseRedirect(reverse('home'))
        return super(UserCreateView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if check_user_ip_ban(request):
            return HttpResponseRedirect(reverse('register_denied_blacklisted'))

        next = request.GET.get('next', None)
        if next:
            pass

        return super(UserCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if check_user_ip_ban(request):
            return HttpResponseRedirect(reverse('register_denied_blacklisted'))
        return super(UserCreateView, self).post(request, *args, **kwargs)

    def form_invalid(self, form):        
        error = form.errors.as_text()
        if 'email' in error:
            error_code = 'email'
        elif 'website' in error:
            error_code = 'bot'
        elif 'name' in error:
            error_code = 'name'            
        elif 'password' in error:
            error_code = 'password'
        else:
            error_code = 'other'

        return self.render_to_json_response({
                    "error": error_code
                })

    def form_valid(self, form):
        from lib.utils import set_unique_top_level_url
        from stats.utils import set_active_users

        # before we let this user in, we need to make sure they aren't on the blacklist!
        try:
            UserBlackList.objects.get(email__iexact=form.cleaned_data['email'])
        except UserBlackList.DoesNotExist:
            pass
        else:
            return HttpResponseRedirect(reverse('register_denied_blacklisted'))

        # check our good friend at 163.com
        if '@163.com' in form.cleaned_data['email']:
            return HttpResponseRedirect(reverse('register_denied_blacklisted'))

        # call the super form_valid which will save the model and prepare our response
        form.instance.first_name = ''.join(form.cleaned_data['name'].split(' ')[:1])
        form.instance.last_name = ''.join(form.cleaned_data['name'].split(' ')[1:])

        response = super(UserCreateView, self).form_valid(form)

        # then we do our own stuff here to setup the user.
        user = self.object
        user.set_password(form.cleaned_data['password'])
        user.accepted_terms = True
        user.slug = set_unique_top_level_url(user.slug, user.pk)

        # grab IP address and log
        ip_address = get_client_ip(self.request)
        if not ip_address == '' and not ip_address == user.last_known_ip:
            user.last_known_ip = ip_address

        user.save()

        UserEmailSettings.objects.get_or_create(user=user)

        next = self.request.GET.get('next', None)

        # Check if the user has been added to a conversation or invited to a Suite
        # chat_invites = ChatInvite.objects.filter(email=user.email)
        # if chat_invites:
        #     from chat.models import ChatMember
        #     from chat.tasks import process_new_chat_member
        #     for invite in chat_invites:
        #         # make the user a chat member
        #         try:
        #             chat_member, created = ChatMember.objects.get_or_create(chat=invite.chat, user=user)
        #             if created:
        #                 process_new_chat_member(chat_member)
        #         except:
        #             pass
        #         invite.delete()

        suite_invites = SuiteInvite.objects.filter(email=user.email)
        if suite_invites:
            for invite in suite_invites:
                # convert the invite into user:user
                invite.email_invite = False
                invite.email = ''
                invite.user_invited = user
                invite.invalidate()
                invite.save()
                fanout_suite_invite.delay(invite, suppress_email=True)

        send_activation_email(user, next=next)
        new_member.delay(user)

        # recount active users
        date_string = datetime.date.today().strftime("%Y-%m-%d")
        set_active_users(date_string)
        
        # user = authenticate(email=user.email, password=user.password)
        user.backend = 'django.contrib.auth.backends.ModelBackend'

        login(self.request, user)
        if user.is_authenticated():
            status = { "success": True }
        else:
            status = { "error": True }
        
        return self.render_to_json_response(status)

        # return response

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        return context

class UserReSendActivationView(View):
    # @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserReSendActivationView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **get_form_kwargss):
        send_activation_email(request.user)
        return HttpResponse('ok')

class UserDeactivateView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        u = request.user
        if not u.is_active:
            raise Http404
        else:
            u.is_active = False
            u.activated = True #just in case not already set; this will allow the user to reactivate later...
            u.save()
            u.invalidate()
        return HttpResponse('ok')

class UserReactivateView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        u = request.user
        if u.is_active:
            raise Http404
        else:
            u.is_active = True
            u.activated = True
            u.save()
            u.invalidate()
        return HttpResponse('ok')

class UserActivateView(RedirectView):
    permanent = False
    user = None
    next = None

    def get(self, request, *args, **kwargs):
        User = get_user_model()
        user = get_object_from_pk(User, pk=kwargs['pk'])

        ''' verify that the user matches the activation key to complete account activation '''
        user = authenticate(email=user.email, key=kwargs['activation_key'], key_type='Activation', password='')
        if not user:
            raise Http404

        # activate the user
        user.activate_user()
        user.invalidate()

        # after successful authentication we should log in the user
        self.user = user
        login(request, user)

        # send a welcome email
        from lib.utils import send_welcome_email
        send_welcome_email(self.user)

        self.next = self.request.GET.get('next', None)

        return super(UserActivateView, self).get(request, args, kwargs)


class UserAuthenticateView(AjaxableResponseMixin, TemplateView):
    template_name = 'static/static_detail.html'
    static_type = auth_type = auth_error = None

    def dispatch(self, request, *args, **kwargs):
        return super(UserAuthenticateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        User = get_user_model()        
        status = 'ok'
        errors = []

        ajax_response = self.request.is_ajax()

        # token = request.POST.get('csrfmiddlewaretoken', '')
        current_url = request.POST.get('currenturl', '')
        auth_type = request.POST.get('authtype', '') 
        email = request.POST.get('email', '')
        fullname = request.POST.get('fullname', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        auth_urls = ['/login', '/register', '/forgot', '/reset']
        # if check_user_ip_ban(request):
        #     return HttpResponseRedirect(reverse('register_denied_blacklisted'))

        if auth_type == 'login':
            if not email:
                errors.append('Please enter your email address.')
            if not password1:
                errors.append('Please type a password.')
            try:
                user = User.objects.get(email=email)
                if not user.check_password(password1):
                    errors.append('Email or password is not valid')
            except:
                errors.append('Email or password is not valid')

            if errors:
                if not ajax_response:
                    messages.error(request, errors[0])
                    return HttpResponseRedirect(reverse('login'))
                else:
                    return self.render_to_json_response({'error': errors[0]})
                    
            exit_url =  current_url if not current_url in auth_urls else '/'
            # grab IP address and log
            ip_address = get_client_ip(request)
            if not ip_address == '' and not ip_address == user.last_known_ip:
                user.last_known_ip = ip_address

            user.last_login = datetime.datetime.now()
            user.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'

            login(request, user)
            if user.is_authenticated():
                status = { 'success': 'userLoggedIn' }
            else:
                status = { 'autherror': 'loginFault' }

            if ajax_response:
                return self.render_to_json_response(status)

            return HttpResponseRedirect(exit_url)
            

        elif auth_type == 'forgot':
            if not email:
                return self.render_to_json_response({'autherror': 'Please enter your email address.'})            
            try:
                user = User.objects.get(email=email)
            except:
                return self.render_to_json_response({'autherror': 'We can\'t find a matching account. Try again or <a href="/support" data-navigate>get in touch</a>.' })      

            # # create and email the new key to the user
            user.create_reset_key()
            send_reset_email(self.request, user)

            # status = { 'success': 'We\'ve sent you an email. Follow the instructions to reset your password.' }
            return self.render_to_json_response(status)

        elif auth_type == 'logout':
            from lib.utils import strip_non_ascii
            referrer = strip_non_ascii(request.META.get('HTTP_REFERER', ''))
            logout(request)
            if self.request.is_ajax():
                return HttpResponse('ok')
            else:
                return redirect('%s%s' % (settings.SITE_URL, referrer), permanent=False)            

        return HttpResponse('ok')

    def get(self, request, *args, **kwargs):
        from django.contrib.messages import get_messages
        
        # check for auth errors (note: this iteration will clear the messages)
        # since we're overwriting, we'll only asign the last one; but we should only ever assign one...
        try:
            messages = get_messages(request)
            for message in messages:
                self.auth_error = str(message)
        except:
            pass

        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        if self.auth_type == ('login' or self.auth_type == 'reg') and request.user.is_authenticated():
            return HttpResponseRedirect(reverse('logout'))
        elif self.auth_type == 'logout' and not request.user.is_authenticated():
            return HttpResponseRedirect(reverse('login'))

        nocontext = ['notfound', 'auth']

        if self.auth_type == 'reset_with_key':
            self.reset_key = kwargs.get('reset_key', '')
            if not self.reset_key:
                return HttpResponseRedirect(reverse('forgot'))
            from profiles.utils import validate_pw_reset_key
            user = self.request.user if self.request.user and self.request.user.is_authenticated() else None
            user_from_key = validate_pw_reset_key(self.reset_key, user)
            self.load_reset_form = True if user_from_key else False

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        return super(UserAuthenticateView, self).get(request, *args, **kwargs)

    def get_inner_context(self):
        standard_login_types = ['login', 'reg', 'forgot', 'logout']
        innercontext = {}
        innercontext['viewType'] = 'auth'

        innercontext['authType'] = self.auth_type
        innercontext['error'] = self.auth_error
        innercontext['%sType' % self.auth_type] = True
        innercontext['currentUrl'] = self.request.get_full_path()
        if self.auth_type in standard_login_types:
            innercontext['standardLogin'] = True

        if self.auth_type == 'reset_with_key':
            innercontext['loadReset'] = self.load_reset_form
            innercontext['resetKey'] = self.reset_key

        from django.core.context_processors import csrf
        innercontext['csrf'] = str(csrf(self.request)['csrf_token'])

        return innercontext


    def get_context_data(self, **kwargs):
        context = super(UserAuthenticateView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()
        context['view_type'] = 'auth'
        context['auth_type'] = self.auth_type
        template = 'static-auth'

        context['static_rendered'] = suite_render(self.request, template, innercontext, False)
        return context

class UserRequestResetView(FormView):
    form_class = RequestResetPasswordForm
    template_name = 'profiles/request_reset.html'
    success_url = reverse_lazy('profile_request_reset_thanks')

    def form_valid(self, form):
        # user is valid, create a reset key
        user = form.get_user()
        user.create_reset_key()
        # email the new key out to the user
        send_reset_email(self.request, user)

        return super(UserRequestResetView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UserRequestResetView, self).get_context_data(**kwargs)
        return context

class UserResetView(AjaxableResponseMixin, FormView):
    form_class = ResetPasswordForm
    template_name = 'profiles/password_reset.html'
    success_url = reverse_lazy('profile_password_reset_thanks')
    pk = None

    def _validate_key(self, request, *args, **kwargs):
        User = get_user_model()
        """ verify that the pk and key match before allowing the form """
        pk = kwargs.get('pk', None)
        reset_key = kwargs.get('reset_key', None)
        if not pk or not reset_key:
            raise Http404

        user = get_object_from_pk(User, pk=pk)
        ''' verify that the username matches the reset key '''
        self.user = authenticate(email=user.email, key=reset_key, key_type='Reset', password='')
        if not self.user:
            raise Http404
        return self.user

    def post(self, request, *args, **kwargs):
        # only allow the reset if it hasn't already expired.
        user = self._validate_key(request, *args, **kwargs)
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        if not user.reset_time or user.reset_time < yesterday:
            user.reset_key = ''
            user.reset_time = None
            user.save()
            raise Http404

        return super(UserResetView, self).get(request, args, kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserResetView, self).get_context_data(**kwargs)
        context['hide_terms'] = True
        return context

    def post(self, request, *args, **kwargs):
        self._validate_key(request, *args, **kwargs)
        return super(UserResetView, self).post(request, args, kwargs)

    def form_valid(self, form):
        user = self.user
        user.is_active = True
        user.reset_key = ''
        user.reset_time = None
        user.set_password(form.cleaned_data.get('password'))
        user.save()
                
        login(self.request, user)

        return super(UserResetView, self).form_valid(form)

class UserRedirectView(RedirectView):
    permanent = True
    pattern_name = 'profile-detail'

    def get_redirect_url(self, *args, **kwargs):
        User = get_user_model()
        user = get_object_from_slug(User, kwargs['slug'], True)
        return user.get_absolute_url()

class UserDetailView(AjaxableResponseMixin, CachedObjectMixin, DetailView):
    User = get_user_model()
    model = User
    template_name = 'profiles/user_detail.html'
    slug = None
    feed_type = None
    suite_empty = False
    hide_user = True

    def dispatch(self, request, *args, **kwargs):
        response = super(UserDetailView, self).dispatch(request, *args, **kwargs)
        return response

    def get_object(self):
        User = get_user_model()
        if self.slug:
            obj = get_object_from_slug(User, self.slug, True, 'profile_image')
            if obj.is_active:
                return obj
            if self.request.user.is_authenticated():
                if self.request.user == obj or self.request.user.is_moderator:
                    return obj
        raise Http404

    def get(self, request, *args, **kwargs):
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.feed = self.other_suites = self.show_more_suites = self.featured_suites = self.suites = []
        self.query = str(self.request.GET.get('q', ''))
        self.named_filter = str(self.request.GET.get('filter', ''))

        # # override feed_type
        # self.feed_type = request.GET.get('feedtype', None)

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
 
        self.object = self.get_object()

        if self.feed_type == "followers":
            self.feed, self.has_next = self.object.get_followers(request, self.page_num)
            self.has_prev = True if self.page_num > 1 else False

        if self.feed_type == "following":
            self.followingType = self.named_filter or 'user'
            self.feed, self.has_next = self.object.get_following(request, follow_type=self.followingType, page=self.page_num)

        if self.feed_type == "suites":
            suites = self.object.get_my_suites(request)
            if suites:
                self.feed = suites

        if not self.feed_type or self.feed_type == "posts":
            if self.query:
                split_querystring = self.query.split('-')
                query = reduce(operator.and_, (Q(title__icontains=x) for x in split_querystring))

                if self.named_filter and self.named_filter=="draft" and self.object == request.user:
                    pks = self.object.posts.drafts().filter(query).values_list('pk', flat=True)[self.start:self.end]            
                else:
                    pks = self.object.posts.published().filter(query).values_list('pk', flat=True)[self.start:self.end]     

            else:
                if self.named_filter and self.named_filter=="draft" and self.object == request.user:
                    pks = self.object.posts.drafts().values_list('pk', flat=True)[self.start:self.end]            
                else:
                    pks = self.object.posts.all().values_list('pk', flat=True)[self.start:self.end]

            if pks: 
                self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
                self.feed = get_serialized_list(self.request, pks,'post:mini')[:DEFAULT_PAGE_SIZE]

        if not self.page_num > 1:
            suites = self.object.get_my_suites(request)
            if suites:
                self.featured_suites = suites[:3]
                if len(suites) > 3:
                    self.other_suites = len(suites[3:])
                    self.show_more_suites = True

        else:
            if not self.feed:
                raise Http404

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                "objects": self.feed,
                "bottomed": False
            })

        return super(UserDetailView, self).get(request, args, kwargs)

    def get_reverse_url(self):
        url_name = 'profile_detail'
        if not self.feed_type:
            url_name = url_name
        else:
            url_name = url_name +    '_' + self.feed_type
        return reverse(url_name, kwargs={'slug': self.object.slug})

    def get_inner_context(self):
        if not self.spa_fetch:
            from profiles.api import UserResource
            innercontext = api_serialize_resource_obj(self.object, UserResource(), self.request)
        else:
            innercontext = {}
        innercontext['currentUrl'] = self.request.get_full_path().split('?')[0]
        innercontext['nextUrl'] = True
        innercontext['namedFilter'] = self.named_filter 

        if self.has_next:
            innercontext['nextLink'] = self.get_reverse_url() + '?page=' + str(self.page_num + 1)           

        if self.has_previous:
            if not self.page_num > 2:       
                innercontext['prevLink'] = self.get_reverse_url()
            else:
                innercontext['prevLink'] = self.get_reverse_url() + '?page=' + str(self.page_num - 1)



        innercontext['featuredSuites'] = self.featured_suites
        innercontext['otherSuites'] = self.other_suites
        innercontext['showMoreSuites'] = self.show_more_suites

        if self.request.user.is_authenticated():
            innercontext['contactable'] = self.object.contactable(self.request.user)
            innercontext['ownerViewing'] = self.request.user == self.object
            innercontext['isMod'] = self.request.user.is_moderator
            
            if self.request.user.is_moderator:
                innercontext['indexed'] = self.object.indexed

            if self.request.user == self.object:
                innercontext['isYou'] = True                  
                innercontext['showBio'] = True

            innercontext['viewerFollowing'] = self.request.user.is_following(self.object.pk, 'user')
            if self.object.privacy == 2:
                innercontext['msg_me'] = True
            elif self.object.privacy == 1 and self.request.user.is_following(self.object.pk, 'user'):
                innercontext['msg_me'] = True

        if not self.feed_type:
            innercontext['homeView'] = True
            innercontext['posts'] = self.feed
            innercontext['nextLink'] = self.get_reverse_url() + '/stories' + str(self.page_num + 1) 

        if self.feed_type == 'posts':
            innercontext['draftFilter'] = True if self.named_filter == 'draft' else False
            innercontext['postsView'] = True
            innercontext['posts'] = self.feed
        
        if self.feed_type == 'suites':
            innercontext['suitesView'] = True
            innercontext['suites'] = self.feed
        
        if self.feed_type == 'followers':
            innercontext['followersView'] = True
            innercontext['followers'] = self.feed

        if self.feed_type == 'following':
            innercontext['followingView'] = True
            innercontext['followingType'] = self.followingType
            innercontext['followingUsers'] = self.feed



        return innercontext

    def get_context_data(self, **kwargs):
        from django.template.loader import render_to_string
        from lib.utils import get_serialized_list
        context = super(UserDetailView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()

        user_json = innercontext.copy()
        context['object'] = self.object
        context['feed_type'] = self.feed_type or ''

        if not self.feed_type:
            if self.page_num < 2:
                context['meta_robots'] = '%s, follow, noodp, noydir' % ('index' if self.object.indexed else 'noindex')
                context['canonical_link'] = self.get_reverse_url()
            else:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url() + '/stories?page=' + str(self.page_num) 

        if self.feed_type == 'posts':
            if self.page_num < 2:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url()
            else:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(self.page_num) 
        
        if self.feed_type == 'suites':
            if self.page_num < 2:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url()
            else:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(self.page_num) 
        
        if self.feed_type == 'followers':
            context['meta_robots'] = 'noindex, follow, noodp, noydir'
            if self.page_num > 1:
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(self.page_num)                
            else:
                context['canonical_link'] = self.get_reverse_url()

        if self.feed_type == 'following':
            context['meta_robots'] = 'noindex, follow, noodp, noydir'
            if self.page_num > 1:
                context['canonical_link'] = self.get_reverse_url() + '?page=' + str(self.page_num)                
            else:
                context['canonical_link'] = self.get_reverse_url()

        if self.has_next:
            next_page_num = self.page_num + 1
            context['has_next'] = True
            if not self.feed_type:
                context['next_link'] = self.get_reverse_url() + '/stories?page=' + str(next_page_num)    
            else:
                context['next_link'] = self.get_reverse_url() + '?page=' + str(next_page_num)

        if self.has_previous:
            prev_page_num = self.page_num - 1
            context['has_prev'] = True
            if not self.page_num > 2:
                context['prev_link'] = self.get_reverse_url()
            elif not self.feed_type:
                context['prev_link'] = self.get_reverse_url() + '/stories?page=' + str(prev_page_num)
            else:
                context['prev_link'] = self.get_reverse_url() + '?page=' + str(prev_page_num)

        author_twitter = "https://twitter.com/%s" % self.object.twitter_username if self.object.twitter_username else ''
        author_facebook = self.object.facebook_url if self.object.facebook_url else ''
        suite_twitter = "https://twitter.com/suiteio"
        suite_facebook = "https://facebook.com/suitestories"

        image = self.object.get_profile_image()
        json_ld = json.dumps({
            "@context":"http://schema.org",
            "@type":"ProfilePage",
            "additionalType":"Person",
            "name":"%s" % self.object.get_full_name(),
            "description":"%s" % self.object.by_line or 'Profile page for %s' % self.object.get_full_name(),
            "url":"https://suite.io%s" % self.object.get_absolute_url(),
            "image": image,
            "sameAs":[ author_facebook, author_twitter ],
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
        context['user_json'] = json.dumps(innercontext)
        context['user_slug'] = self.object.slug
        context['user_detail_rendered'] = suite_render(self.request, 'user-detail', innercontext)

        if self.object.approved:
            context['follow'] = True

        return context

class UserSettingsView(AjaxableResponseMixin, TemplateView):
    template_name = 'profiles/settings_detail.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserSettingsView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        import requests, json, urllib, re
        from profiles.models import UserEmailSettings
        if not request.user and request.user.is_authenticated():
            raise Http404

        change_slug = True if request.POST.get('changeslug', '') == 'true' else False 
        change_password = True if request.POST.get('changepw', '') == 'true' else False 
        ga_code_update = True if request.POST.get('gacodeupdate', '') == 'true' else False 
        priv_settings = True if request.POST.get('setpriv', '') == 'true' else False 
        email_prefs = True if request.POST.get('emailprefs', '') == 'true' else False

        def encoded_dict(in_dict):
            out_dict = {}
            for k, v in in_dict.iteritems():
                if isinstance(v, unicode):
                    v = v.encode('utf8')
                elif isinstance(v, str):
                    # Must be encoded in UTF-8
                    v.decode('utf8')
                out_dict[k] = v
            return out_dict

        def is_clean(slug):
            pattern = re.compile("^[a-zA-Z0-9-_]+$")
            if pattern.match(slug):
                return True
            return False

        if change_slug:
            from lib.utils import get_slug_status
            slug = request.POST.get('slug', '')
            if not is_clean(slug):
                return self.render_to_json_response({'error': 'must be alphanumeric etc, etc'})

            if slug == request.user.slug:
                return self.render_to_json_response({'error': 'nochange'})

            slug_status = get_slug_status(slug, request.user)
            if slug_status['error']:
                status = slug_status['error']
            else:
                request.user.slug = slug
                request.user.save()
                status = {'ok': True}                
                from lib.tasks import invalidate_user_slugs
                invalidate_user_slugs.delay(request.user)
            return self.render_to_json_response(status)

        if change_password:
            pw = request.POST.get("pw", "")
            pw2 = request.POST.get("pw2", "")

            if not pw == pw2:
                return self.render_to_json_response({'error': 'nomatch'})

            request.user.set_password(pw)
            return HttpResponse('ok')            

        if ga_code_update:
            code = request.POST.get("code", "")

            if not code:
                raise Http404

            if code == request.user.ga_code:
                response = 'unchanged'
            else:   
                request.user.ga_code = code
                request.user.invalidate()
                request.user.save()
                response = 'changed'
            return HttpResponse(response)

        if priv_settings:
            setting = int(request.POST.get("set", ""))  
            if not setting:
                raise Http404 
            self.request.user.privacy = setting
            self.request.user.save()
            self.request.user.invalidate()
            return HttpResponse('ok')

        if email_prefs:
            setting = request.POST.get("set", "")  
            email_settings, created = UserEmailSettings.objects.get_or_create(user=request.user)
            if setting == 'daysum':
                if email_settings.daily_summary:
                    email_settings.daily_summary = False
                else:
                    email_settings.daily_summary = True

            if setting == 'stories':
                if email_settings.new_posts:
                    email_settings.new_posts = False
                else:
                    email_settings.new_posts = True
                
            if setting == 'notifs':
                if email_settings.notifications:
                    email_settings.notifications = False
                else:
                    email_settings.notifications = True

            if setting == 'weekly':
                if email_settings.weekly_digest:
                    email_settings.weekly_digest = False
                else:
                    email_settings.weekly_digest = True

            email_settings.save()
            request.user.invalidate()
            return HttpResponse('ok')

        # TODO: return fresh counts
        return HttpResponse('ok')

    def get(self, request, *args, **kwargs):
        from django.template.loader import render_to_string
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        return super(UserSettingsView, self).get(request, *args, **kwargs)

    def get_inner_context(self):
        from profiles.api import UserResource
        innercontext = api_serialize_resource_obj(self.request.user, UserResource(), self.request)
        
        innercontext['email'] = self.request.user.email
        innercontext['mySlug'] = self.request.user.slug
        innercontext['location'] = self.request.user.location
        innercontext['personalUrl'] = self.request.user.personal_url
        innercontext['adsEnabled'] = self.request.user.ads_enabled
        innercontext['active'] = True if self.request.user.is_active else False                            
        innercontext['gaCode'] = self.request.user.ga_code

        # Email settings
        innercontext['emailSettings'] = {}
        innercontext['emailSettings']['daily'] = True if self.request.user.email_settings.daily_summary else False
        innercontext['emailSettings']['stories'] = True if self.request.user.email_settings.new_posts else False
        innercontext['emailSettings']['notifs'] = True if self.request.user.email_settings.notifications else False
        innercontext['emailSettings']['weekly'] = True if self.request.user.email_settings.weekly_digest else False

        return innercontext

    def get_context_data(self, **kwargs):
        context = super(UserSettingsView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()
        context['settings_json_str'] = json.dumps(innercontext)
        context['settings_rendered'] = suite_render(self.request, 'settings-shell', innercontext)
        return context
      
class UserPasswordChangeView(AjaxableResponseMixin, CachedObjectMixin, FormView):
    form_class = ResetPasswordForm
    template_name = 'profiles/password_change.html'  # doesn't get used
    success_url = '/settings'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserPasswordChangeView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        self.object = self.request.user
        self.object.set_password(form.cleaned_data.get('password'))
        self.object.save()
        return super(UserPasswordChangeView, self).form_valid(form)

from social.apps.django_app.utils import psa
from social.actions import do_disconnect
from django.contrib.auth import REDIRECT_FIELD_NAME
@login_required
@psa()
def social_disconnect(request, backend, association_id=None):
    """Disconnects given backend from current logged in user."""
    return do_disconnect(request.backend, request.user, association_id,
                         redirect_name=REDIRECT_FIELD_NAME)

class UserPasswordSetView(CachedObjectMixin, FormView):
    form_class = ResetPasswordForm
    template_name = 'profiles/set_password.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.backend = kwargs.get('backend')
        return super(UserPasswordSetView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserPasswordSetView, self).get_context_data(**kwargs)
        context['backend'] = self.backend
        return context

    def form_valid(self, form):
        self.object = self.request.user
        self.object.set_password(form.cleaned_data.get('password'))
        self.object.save()
        return super(UserPasswordSetView, self).form_valid(form)

    def get_success_url(self):
        return reverse('profile_social_disconnect', kwargs={'backend': self.backend})


class UserEmailChangeView(AjaxableResponseMixin, CachedObjectMixin, FormView):
    form_class = ChangeEmailForm
    template_name = 'profiles/email_change.html'  # doesn't get used
    http_method_names = ['post']
    success_url = '/'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserEmailChangeView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        self.object = self.request.user
        self.object.set_new_email(form.cleaned_data.get('email'))
        # self.object.save()  # the set_new_email already does a save!
        
        send_email_change_email(self.request, self.object)
        return super(UserEmailChangeView, self).form_valid(form)

class UserCompleteEmailChangeView(RedirectView):
    permanent = False

    def get(self, request, *args, **kwargs):
        User = get_user_model()
        user = get_object_from_pk(User, pk=kwargs['pk'])

        ''' verify that the user matches the activation key to complete account activation '''
        user = authenticate(email=user.email, key=kwargs['email_key'], key_type='Email', password='')
        if not user:
            return HttpResponseRedirect(reverse('profile_email_change_expired'))

        # only allow the reset if it hasn't already expired.
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        if not user.email_change_time or user.email_change_time < yesterday:
            user.new_email = ''
            user.email_key = ''
            user.email_change_time = None
            user.save()
            return HttpResponseRedirect(reverse('profile_email_change_expired'))

        # activate the user
        user.complete_email_change()

        # after successful authentication we should log in the user
        login(request, user)

        return super(UserCompleteEmailChangeView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        return reverse('home')

class UserUploadImageView(AjaxableResponseMixin, CachedObjectMixin, CreateView):
    form_class = UserUploadImageForm
    template_name = 'profiles/upload.html'  # doesn't get used.
    success_url = '/'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserUploadImageView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        image = form.save()
        success, image_url = resize_profile_image(image)
        if not success:
            raise forms.ValidationError(_('There was a problem processing your image. Please try again'))
        return super(UserUploadImageView, self).form_valid(form, extra_data={'image_url': image_url})


class UserFollowView(GenericFollowView):
    def dispatch(self, *args, **kwargs):
        User = get_user_model()
        kwargs['model_object'] = User
        return super(UserFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.tasks import send_email_alert, process_new_follow
        from profiles.sets import UserFollowersSet, UserFollowsUsersSet

        response = super(UserFollowView, self).post(request, *args, **kwargs)

        followed = self.obj
        follower = request.user

        # build and send the stats event
        stat_value = 1
        event = {
            "event": "followers",
            "followed": followed.pk,
            "follower": follower.pk,
            "foltype": "user",
            "value": stat_value
        }
        process_local_stats_event(event, self.request)
        process_new_follow(self.follow)
        return response


class UserUnFollowView(GenericUnFollowView):
    def dispatch(self, *args, **kwargs):
        kwargs['model_object'] = get_user_model()
        return super(UserUnFollowView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from lib.tasks import process_unfollow
        from profiles.sets import UserFollowersSet, UserFollowsUsersSet
        response = super(UserUnFollowView, self).post(request, *args, **kwargs)

        unfollowed = self.obj
        unfollower = request.user

        # build and send the stats event
        stat_value = -1
        event = {
            "event": "followers",
            "followed": unfollowed.pk,
            "follower": unfollower.pk,
            "foltype": "user",
            "value": stat_value
        }
        process_local_stats_event(event, self.request)
        process_unfollow(unfollowed, request.user)
   
        return response

class UserDeleteView(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserDeleteView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        # double-check user has confirmed this action!
        confirmed = True if request.POST.get("confirmed", False) == 'true' else False  
        user = self.request.user
        user.delete()
        logout(self.request)

        return HttpResponseRedirect('/')

# class UserStoryExportView(View):
    # import pdfkit
    # import os
    # import zipfile

    # TODO: 1) choose format (PDF, plain-text + images)
    #       2) build downloadable zip file
    #       3) download + email to user

    # pdfkit.from_url('http://google.com', 'out.pdf')
    # http://stackoverflow.com/questions/23359083/how-to-convert-webpage-into-pdf-by-using-python

    # Zip up the files
    # http://stackoverflow.com/questions/14568647/create-zip-in-python

    # def zip(src, dst):
    #     zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    #     abs_src = os.path.abspath(src)
    #     for dirname, subdirs, files in os.walk(src):
    #         for filename in files:
    #             absname = os.path.abspath(os.path.join(dirname, filename))
    #             arcname = absname[len(abs_src) + 1:]
    #             print('zipping %s as %s' % (os.path.join(dirname, filename),
    #                                         arcname))
    #             zf.write(absname, arcname)
    #     zf.close()

    # zip("src", "dst")

class UserArticleDumpView(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        User = get_user_model()
        self.user = get_object_from_pk(User, kwargs.get('pk'))
        if not self.user == self.request.user or not self.request.user.is_moderator:
            raise Http404
        return super(UserArticleDumpView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        import html2text
        import time
        import datetime

        articles = self.user.articles.all()
        content = []

        for article in articles:
            images = article.images.all()

            content += '\n\n'
            content += '----------------------------------------------------------------------------- \n\n'
            content += 'Title: %s\n' % article.title
            content += 'Intro: %s\n' % article.subtitle
            content += 'Created: %s\n' % article.created.strftime("%Y-%m-%d")
            content += '\n\n'
            try:
                content += html2text.html2text(article.body.content)
            except:
                content += article.body.content
            if images:
                content += '\n\n'
                content += 'Images: \n'
                for image in images:
                    content += '%s \n' % image.get_large_image_url()

        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="%s.txt"' % (self.user.get_full_name())

        return response

class UserGetPeopleView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(UserGetPeopleView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        following, next = request.user.get_following(request)

        return self.render_to_json_response({
            "objects": following
        })

class UserGetPostsView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(UserGetPostsView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        return self.render_to_json_response({
            "objects": request.user.get_user_stories(request)
        })

class UserGetSuitesView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(UserGetSuitesView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        return self.render_to_json_response({
            "objects": request.user.get_my_suites(request)
        })

class GetUserFromPk(AjaxableResponseMixin, View):
    @method_decorator(never_cache)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_from_pk(get_user_model(), int(kwargs.get('pk')), False) 
        return super(GetUserFromPk, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        if not self.user:
            raise Http404

        user_object = []
        from profiles.api import UserMiniResource
        
        try:
            user_object = api_serialize_resource_obj(self.user, UserMiniResource(), request)
        except Exception as e:
            pass

        return self.render_to_json_response(user_object)


class FeedView(AjaxableResponseMixin, TemplateView):
    template_name = 'profiles/feed_detail.html'

    def dispatch(self, *args, **kwargs):
        return super(FeedView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        from articles.models import Article
        from lib.utils import get_serialized_list, get_recommended_stories, get_lead_story
        pks = []
        self.feed = []
        self.lead_story = None
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.feed_type = request.GET.get('feedtype', '') or 'all'
        please_rebuild = True if request.GET.get('fetchType') == 'rebuild' else False
        self.rebuildMe = 0

        if please_rebuild:
            from lib.utils import rebuild_user_feed
            try:
                added = rebuild_user_feed(request.user)
            except:
                added = 0
            return HttpResponse(added)

        try:
            self.page_num = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page_num = 1

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = True 

        self.next_page_num = self.page_num + 1
        self.next_link = settings.SITE_URL + '?page=' + str(self.next_page_num) 

        self.prev_page_num = self.page_num - 1 if self.has_previous else 0    
        self.prev_link = settings.SITE_URL + '?page=' + str(self.prev_page_num) if self.has_previous else None
        
        if not request.user.is_authenticated():
            pks = get_recommended_stories()[self.start:self.end]
            self.feed = get_serialized_list(request, pks[:DEFAULT_PAGE_SIZE],'story:mini')

            lead = get_lead_story()
            if lead:
                self.lead_story = get_serialized_list(self.request, [lead],'story:mini')[0]

        else:
            import time
            from articles.sets import UserMainStoryFeed

            if self.feed_type == 'all':
                pks = UserMainStoryFeed(request.user.pk).get_set(self.page_num)
                if not self.page_num > 1 and not pks:
                    self.rebuildMe = 1 if self.request.user.needs_feed() else 0
                self.feed = get_serialized_list(request, pks,'story:mini')

        if pks:
            self.has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
        
        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            if not self.feed:
                raise Http404
            return self.render_to_json_response({
                    "objects": self.feed
                })

        return super(FeedView, self).get(request, args, kwargs)      

    def get_inner_context(self):
        innercontext = {}
        innercontext['userLoggedIn'] = self.request.user.is_authenticated()
        innercontext['currentUrl'] = self.request.get_full_path().split('?')[0]
        innercontext['title'] = 'Suite'
        innercontext['prevPage'] = self.prev_page_num
        innercontext['prevLink'] = self.prev_link
        innercontext['nextPage'] = self.next_page_num
        innercontext['nextLink'] = self.next_link
                
        if self.page_num > 1:
            innercontext['currentPage'] = self.page_num     

        if self.request.user.is_authenticated():
            innercontext['storyFeed'] = self.feed
            innercontext['rebuildMe'] = self.rebuildMe

            if self.feed_type == 'all' or not self.feed_type:
                innercontext['allFilter'] = True
            elif self.feed_type == 'long':
                innercontext['longFilter'] = True
            elif self.feed_type == 'popular':
                innercontext['readFilter'] = True

        else:
            innercontext['stories'] = self.feed
            innercontext['leadStory'] = self.lead_story

        return innercontext

    def get_context_data(self, **kwargs):
        import time
        from lib.utils import get_serialized_list, get_featured_suites
        from articles.sets import UserMainStoryFeed
        context = super(FeedView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()     

        if self.request.user.is_authenticated():
            tmpl = 'feed'
            context['rebuildMe'] = self.rebuildMe
        else:                               
            tmpl = 'home' 

        context['feed_rendered'] = suite_render(self.request, tmpl, innercontext, False)
        context['page_num'] = self.request.GET.get('page', '1')
        context['has_next'] = self.has_next
        context['next_link'] = self.next_link
        context['has_prev'] = self.has_previous
        context['prev_link'] = self.prev_link

        if self.page_num < 2:
            context['title'] = 'Suite'
            context['meta_robots'] = 'index, follow, noodp, noydir'
            context['canonical_link'] = settings.SITE_URL
        else:
            context['meta_robots'] = 'noindex, follow, noodp, noydir'
            context['canonical_link'] = '?page=' + str(self.page_num) 
            context['title'] = 'Featured posts from all around Suite - page %s' % self.page_num

        context['current_url'] = self.request.get_full_path().split('?')[0]
        context['feed_json_str'] = json.dumps(innercontext)
 
        context['feed_rendered'] = suite_render(self.request, tmpl, innercontext)
        return context
           
class UserContactableView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_from_pk(User, int(kwargs.get('pk')), False) 
        return super(UserContactableView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        contactable = request.user.contactable(self.user)
        return HttpResponse(contactable)

class UserNeighbourSearch(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(UserNeighbourSearch, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):        
        from profiles.api import UserMiniResource
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        split_querystring = None
        objects = []
        User = get_user_model()

        querystring = str(request.GET.get('q', ''))
        if querystring:
            query = querystring[:querystring.find('?')]
            split_querystring = querystring.split('-')

        self.named_filter = str(self.request.GET.get('filter', ''))

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
        pks = None
        results = []    

        if not split_querystring:
            raise Http404

        if split_querystring:
            query = reduce(operator.and_, (Q(full_name__icontains=x) for x in split_querystring))
            pks = User.objects.annotate(full_name=Concat('first_name', V(' '), 'last_name')).filter(query).values_list('pk', flat=True)
            if pks:
                objects = get_serialized_list(request, pks, 'user:mini')

            return self.render_to_json_response({
                    "objects": objects
                }) 

    def post(self, request, *args, **kwargs):
        from django.http import HttpResponse
        # from conversation.models import Conversation
        from suites.models import Suite
        from profiles.sets import FeaturedMemberSet
        from lib.utils import get_serialized_list, diff, seems_like_email
        from profiles.sets import UserFollowsUsersSet, UserFollowersSet
        from lib.sets import RedisObject
        import time
        User = get_user_model()
        start_time = time.time() # start stopwatch
        user = request.user
        query = request.POST.get("q", "")

        is_new = request.POST.get("isnew", "")
        suite_invite = True if request.POST.get("invite", False) else False
        exclusions_string = request.POST.get("exclusions", "")
        exclusions = exclusions_string.split(',')

        email = ""
        self.object_id = request.POST.get("objectid", "")
        object_type = request.POST.get("objtype", "")
        objects = []

        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()

        def return_nothing():
            return self.render_to_json_response({
                "objects": []
            })

        members = []
        if is_new:
            members = exclusions

        else:
            try:
                if object_type and object_type == "suite":
                    suite = get_object_from_pk(Suite, self.object_id) 
                    mems, requested_users, invited_users = suite.get_users()
                    members = mems + requested_users + invited_users

                # if object_type and object_type == "chat":
                #     chat = get_object_from_pk(Chat, self.object_id)            
                #     members = chat(get_member_pks)

            except:
                pass
        # note: we suggest a list of mutual follows as the default queryset
        if not query:
            mutual_follows = user.get_mutual_follows() # returns pks
            excluding_members = diff(mutual_follows,members) if members and mutual_follows else None

            if not excluding_members:
                return_nothing()

            return self.render_to_json_response({
                "objects": get_serialized_list(request, excluding_members,'user')
            })

        else:
            from django.db.models import Q
            from profiles.sets import UserFollowersSet, AnybodiesSet

            # email?
            if str('@') in query:
                if seems_like_email(query):
                    email = query

                    # try to get a user object (look for many, pick the first)
                    users_from_email = User.objects.filter(email=email)
                    if users_from_email:
                        if users_from_email[0].contactable(request.user):
                            try:
                                objects = get_serialized_list(request, [users_from_email[0].pk],'user:mini')
                                objects[0]['email'] = email
                                objects[0]['byEmail'] = True
                                return self.render_to_json_response({
                                    "objects": objects
                                })
                            except Exception as e:
                                return_nothing()
                    
                    return self.render_to_json_response({
                        "objects": [{
                            'email': email,
                            'byEmail': True
                        }]
                    })

            STAFFERS = [7444, 7455]
            # TODO: fb + twitter friends who are members but not mutfols - external mutfols
            mutfols = user.get_mutual_follows() # returns pks
            contactable = mutfols + STAFFERS
            
            users = User.objects.filter(pk__in=list(contactable)) # people the request user is allowed to contact

            users_found = map(str, users.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)).values_list('pk', flat=True))
            excluding_members = diff(users_found, members) if members else users_found

            if excluding_members:
                objects = get_serialized_list(request, excluding_members,'user:mini')
                if suite_invite:
                    for obj in objects:
                        obj['invited'] = True

                return self.render_to_json_response({
                    "objects": objects
                })

            return HttpResponse('ok')


