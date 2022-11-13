import json, time
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.template.defaultfilters import date, title, cut, escape
from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.conf.urls import url
from django.http import Http404
from django.core.paginator import Paginator, InvalidPage

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.constants import ALL
from tastypie.bundle import Bundle

from lib.api import Suite101Resource, Suite101SearchResource, Suite101BaseAuthorization, Suite101ModelFormValidation
from lib.models import Follow
from lib.mixins import AjaxableResponseMixin
from lib.enums import DEFAULT_PAGE_SIZE
from lib.cache import get_object_from_pk
from lib.utils import api_serialize_resource_obj, get_serialized_list

from articles.templatetags.ptag import bio
from django.utils.html import strip_tags
from articles.templatetags.bleach_filter import bleach_filter

from .forms import UserUpdateForm
from .models import UserImage

class UserAuthorization(Suite101BaseAuthorization):
    def create_list(self, object_list, bundle):
        # don't allow create for now - use the views
        return False

    def read_detail(self, object_list, bundle):
        """ anyone can see any active user """
        if bundle.obj.is_active:
            return True
        if bundle.request.user.is_authenticated():
            if bundle.obj == bundle.request.user or bundle.request.user.is_moderator:
                return True
        return False

    def create_detail(self, object_list, bundle):
        # don't allow create for now - use the views
        return False

    def update_detail(self, object_list, bundle):
        return bundle.obj == bundle.request.user or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        # don't allow delete for now - use the views
        return False

class UserMiniResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        User = get_user_model()
        data_cache_key = 'user:mini'
        resource_name = 'user_mini'
        detail_uri_name = 'slug'
        queryset = User.objects.filter()
        authorization = UserAuthorization()
        detail_allowed_methods = ['get']
        list_allowed_methods = ['get']
        always_return_data = True

        fields = [
            'id',
            'slug'
        ]

    def prepend_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<slug>[-_\w]+)/$' % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}
        if isinstance(bundle_or_obj, Bundle):
            kwargs['slug'] = bundle_or_obj.obj.slug
        else:
            kwargs['slug'] = bundle_or_obj.slug
        return kwargs

    def dehydrate(self, bundle):
        user = bundle.obj
        # Core member stats

        bundle.data['id'] = user.pk
        bundle.data['obj_type'] = 'user'
        bundle.data['full_name'] = title(user.full_name)
        bundle.data['first_name'] = user.first_name
        bundle.data['by_line'] = user.by_line
        bundle.data['main_image_url'] = user.get_profile_image()
        bundle.data['date_joined'] = time.mktime(user.date_joined.timetuple())
        bundle.data['app'] = user.approved        
        bundle.data['fea'] = True if user.featured else False
        bundle.data['active'] = user.is_active
        
        if user.is_staff:
            bundle.data['is_staff'] = True
        elif user.is_moderator:
            bundle.data['is_ed'] = True
        return bundle

class UserResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        data_cache_key = 'user:full'  
        cache_authed = False          
        User = get_user_model()
        detail_uri_name = 'slug'
        resource_name = 'user'
        queryset = User.objects.all()
        authorization = UserAuthorization()
        validation = Suite101ModelFormValidation(form_class=UserUpdateForm)
        always_return_data = True

        fields = [
            'first_name',
            'last_name',
            'by_line',
            'ga_code',
            'location',
            'profile_image',
            'approved',
            'slug',
            'show_email',
            'privacy',
            'email_settings'
        ]

    def prepend_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<slug>[-_\w]+)/$' % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}
        if isinstance(bundle_or_obj, Bundle):
            kwargs['slug'] = bundle_or_obj.obj.slug
        else:
            kwargs['slug'] = bundle_or_obj.slug
        return kwargs

    def dehydrate(self, bundle):
        user = bundle.obj
        bundle.data['id'] = user.pk
        bundle.data['stats'] = user.get_user_stats()
        bundle.data['date_joined'] = date(user.date_joined, "M j, Y") 
        bundle.data['full_name'] = title(user.get_full_name())
        bundle.data['main_image_url'] = user.get_profile_image()
        bundle.data['facebook_connected'] = user.facebook_connected
        bundle.data['facebook_url'] = user.facebook_url
        bundle.data['twitter_username'] = user.twitter_username
        bundle.data['tweet_params_encoded'] = user.tweet_params_encoded()
        bundle.data['personal_url'] = user.personal_url
        bundle.data['personal_url_trimmed'] = cut(user.personal_url,"http://")
        bundle.data['location'] = user.location        
        bundle.data['show_email'] = user.show_email
        bundle.data['privacy'] = user.privacy
        bundle.data['priv%s' % user.privacy]  = True
        if bundle.data['show_email']:
            bundle.data['email'] = user.email

        bundle.data['absolute_url'] = user.get_absolute_url()

        if user.tag_list:
            try:
                tags = json.loads(str(user.tag_list))
                tags_obj = []
                for tag in tags:
                    tags_obj.append({
                        'tag': tag
                    })
                bundle.data['tag_list'] = tags_obj[:5]
                if len(tags_obj) > 5:
                    bundle.data['more_tags'] = True
                    bundle.data['tags_list_more'] = tags_obj[5:]
            except Exception as e:
                pass

        if hasattr(bundle.request, 'user') and bundle.request.user.is_authenticated():
            bundle.data['ownerViewing'] = bundle.request.user == user
            if bundle.request.user.is_moderator:
                bundle.data['is_mod'] = True
                bundle.data['featured'] = user.featured

                bundle.data['app'] = user.approved
                bundle.data['is_staff'] = user.is_staff
                bundle.data['is_moderator'] = user.is_moderator
                bundle.data['active'] = user.is_active

        return bundle

    def hydrate(self, bundle):
        if 'suites' in bundle.data:
            del bundle.data['suites']
        if 'stories' in bundle.data:
            del bundle.data['stories']
        if 'approved' in bundle.data:
            del bundle.data['approved']
        return bundle

    def obj_update(self, bundle, **kwargs):
        response = super(UserResource, self).obj_update(bundle, **kwargs)
        from lib.utils import check_unique_top_level_url

        if 'email_prefs' in bundle.data:
            try:
                prefs = bundle.data['email_prefs']
                pref_prop = prefs['prop']
                pref_value = prefs['propvalue']

                model_prefs = bundle.request.user.email_settings
                setattr(model_prefs, pref_prop, pref_value)
                model_prefs.save()  

            except Exception as e:
                print(e)

        if 'personal_url' in bundle.data:
            try:
                bundle.obj.personal_url = bundle.data['personal_url']
            except Exception as e:
                print(e)

        profile_image_pk = None
        if 'profile_image' in bundle.data:
            profile_image_pk = bundle.data['profile_image']
            del bundle.data['profile_image']

        if profile_image_pk:
            profile_image = get_object_from_pk(UserImage, profile_image_pk, False)
            if profile_image:
                if bundle.obj.profile_image and not bundle.obj.profile_image == profile_image:
                    bundle.obj.profile_image.delete()
                profile_image.user = bundle.obj
                profile_image.save()
                bundle.obj.profile_image = profile_image

        bundle.obj.save()
        bundle.obj.invalidate()

        return response

class UserSearchResource(Suite101SearchResource):
    class Meta:
        User = get_user_model()
        model = User
        queryset = User.objects.all()
        resource_name = 'users'
        url_name = 'api_user_search'

    # def get_default_queryset(self):
    #     return self._meta.model.objects.filter(featured=True)
    def get_serialized_objs(self, request, obj_list): 
        try:
            objects = get_serialized_list(request, obj_list, 'user:mini')
        except Exception as e:
            return []
        return objects


    def serialize_obj(self, obj):
        return api_serialize_resource_obj(obj, UserResource(), HttpRequest())


class UserEmailSearchResource(Suite101SearchResource):  
    class Meta:
        User = get_user_model()
        model = User
        queryset = User.objects.all()
        resource_name = 'users_email'
        url_name = 'api_user_email_search'

    def get_default_queryset(self):
        return self._meta.model.objects.filter(approved=True)

    def serialize_obj(self, obj):
        return api_serialize_resource_obj(obj, UserResource(), HttpRequest())

    def do_search(self, request, **kwargs):
        User = get_user_model()
        if not request.user.is_authenticated():
            return [], None

        query = request.GET.get('q', '')
        users = User.objects.filter(email__iexact=query)
        paginator = Paginator(users, DEFAULT_PAGE_SIZE)
        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except InvalidPage:
            raise Http404('Sorry, no results on that page.')

        objects = []

        for result in page.object_list:
            objects.append(self.serialize_obj(result))

        return objects, page
