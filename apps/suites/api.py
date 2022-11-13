from django.conf.urls import url
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.template.defaultfilters import title, timesince, truncatechars
from django.contrib.humanize.templatetags.humanize import intcomma
from django.http import HttpRequest, Http404
import random
import json
import time

from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.validation import FormValidation, Validation
from tastypie.bundle import Bundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import Resource

from profiles.api import UserMiniResource
from lib.utils import api_serialize_resource_obj, get_serialized_list
from lib.tasks import resize_suite_hero_image, send_email_alert
from lib.models import Follow
from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from lib.cache import get_object_from_pk
from articles.models import ArticleImage, Article
from links.models import Link
from .models import Suite, SuitePost, SuiteImage, SuiteInvite, SuiteRequest, SuiteMember
from .forms import SuiteCreateForm, SuiteInviteForm, SuiteRequestForm, SuiteImageAttrsUpdateForm

from django.template.defaultfilters import truncatechars
from articles.templatetags.bleach_filter import bleach_filter
from articles.templatetags import upto
from tastypie.constants import ALL_WITH_RELATIONS

class SuiteAuthorization(Suite101BaseAuthorization):
    def read_detail(self, object_list, bundle):
        if not bundle.obj.owner.is_active:
            raise Http404

        if bundle.obj.private:
            if not bundle.request.user.is_authenticated():
                raise Http404
            elif not bundle.request.user.member_of(bundle.obj) and not bundle.request.user.invited_to(bundle.obj):
                raise Http404    
        return True

    def update_detail(self, object_list, bundle):
        return bundle.obj.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user or \
                bundle.request.user.is_moderator

class SuiteImageAuthorization(Suite101BaseAuthorization):
    def update_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

class SuiteImageResource(Suite101Resource):
    user = fields.ToOneField(UserMiniResource, 'user', null=True)
    suite = fields.ToOneField('suites.api.SuiteResource', 'suite', null=True)

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite_image'
        data_cache_key = 'suite:img'
        queryset = SuiteImage.objects.all()
        authorization = SuiteImageAuthorization()
        validation = FormValidation(form_class=SuiteImageAttrsUpdateForm)
        include_absolute_url = False
        always_return_data = True

        fields = [
            'id',
            'caption',
            'credit',
            'credit_link'
        ]

    def dehydrate(self, bundle):
        bundle.data['orig_image_url'] = bundle.obj.get_orig_image_url()
        bundle.data['large_image_url'] = bundle.obj.get_large_image_url()
        bundle.data['small_image_url'] = bundle.obj.get_small_image_url()
        return bundle

    def hydrate(self, bundle):
        if 'orig_image_url' in bundle.data:
            del bundle.data['orig_image_url']
        if 'large_image_url' in bundle.data:
            del bundle.data['large_image_url']
        if 'small_image_url' in bundle.data:
            del bundle.data['small_image_url']
        return bundle

class SuiteMiniResource(Suite101Resource):
    owner = fields.ToOneField(UserMiniResource, 'owner')
    # hero_image = fields.ToOneField(SuiteImageResource, 'hero_image', full=True, null=True)

    class Meta(Suite101Resource.Meta):
        obj_cache_key = 'suite:obj'
        data_cache_key = 'suite:mini'
        resource_name = 'suite_mini'
        queryset = Suite.objects.all()
        authorization = ReadOnlyAuthorization()

        fields = [
            'id',
            'slug',
        ]

        filtering = {
            'owner': 'exact'
        }

    def dehydrate(self, bundle):
        suite = bundle.obj
        bundle.data['obj_type'] = 'suite'
        bundle.data['stats'] = suite.get_suite_stats()
        bundle.data['name'] = title(suite.name)
        # bundle.data['owner'] = api_serialize_resource_obj(suite.owner, UserMiniResource(), bundle.request)
        bundle.data['private'] = suite.private
        bundle.data['obj_type'] = 'suite'
        bundle.data['suite_type'] = True        
        
        featured_members = suite.get_featured_members(bundle.request)
        if featured_members:
            bundle.data['featured_members'] = featured_members
            bundle.data['other_members'] = len(featured_members) - 1 if len(featured_members) > 1 else 0 

        bundle.data['image'] = suite.get_hero_image(bundle.request)        
        
        bundle.data['short_description'] = truncatechars(bleach_filter(suite.description, ['p']), 100)
        bundle.data['resource_uri'] = SuiteResource().get_resource_uri(suite)
        bundle.data['show_owner'] = False
        return bundle

class SuiteResource(Suite101Resource):
    owner = fields.ToOneField(UserMiniResource, 'owner')
    hero_image = fields.ToOneField(SuiteImageResource, 'hero_image', null=True)

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite'
        data_cache_key = 'suite:full'  
        cache_authed = False
        queryset = Suite.objects.all()
        authorization = SuiteAuthorization()
        validation = Suite101ModelFormValidation(form_class=SuiteCreateForm)
        always_return_data = True
        post_process_image = False

        fields = [
            'id',
            'name',
            'about',
            'description',
            'about',
            'private',
            'slug',
            'parent'
        ]

        filtering = {
            'owner': 'exact'
        }

    def dehydrate(self, bundle):
        suite = bundle.obj

        bundle.data['image'] = suite.get_hero_image(bundle.request)
        # Core suite stats
        from stats.sets import SuiteStats
        bundle.data['stats'] = suite.get_suite_stats()
        # Main attributes
        bundle.data['owner'] = api_serialize_resource_obj(suite.owner, UserMiniResource(), bundle.request)

        bundle.data['name'] = suite.name
        bundle.data['tweet_params_encoded'] = suite.tweet_params_encoded()
        bundle.data['pin_params_encoded'] = suite.pin_params_encoded()
        bundle.data['featured'] = True if suite.featured else False
        bundle.data['show_owner'] = True
        bundle.data['hash'] = suite.hashed_id
        bundle.data['modified'] = time.mktime(suite.modified.timetuple())
        bundle.data['userLoggedIn'] = bundle.request.user.is_authenticated()

        bundle.data['featured_members'] = suite.get_featured_members(bundle.request)
        featured_members = suite.get_featured_members(bundle.request)
        bundle.data['other_members'] = len(featured_members) - 1 if len(featured_members) > 1 else 0   

        if hasattr(bundle.request, 'user') and bundle.request.user.is_authenticated():

            # Suite management stuff
            invites, requests = suite.get_pending_data(bundle.request)

            bundle.data['num_invites'] = invites
            bundle.data['num_requests'] = requests

            bundle.data['viewer_following'] = bundle.request.user.is_following(suite, 'suite')
            
            bundle.data['viewer_is_member'] = bundle.request.user.member_of(suite)
            
            pending_type = suite.is_pending(bundle.request.user)
            if pending_type:
                bundle.data['viewer_pending'] = True
                if pending_type == "requested":
                    bundle.data['viewer_request'] = True
                elif pending_type == "invited":
                    bundle.data['viewer_invited'] = True

            if suite.is_editor(bundle.request.user.pk):
                bundle.data['ed_viewing'] = True

            if bundle.request.user == suite.owner:
                bundle.data['owner_viewing'] = True

            if bundle.request.user.is_moderator:
                bundle.data['is_mod'] = True
                # bundle.data['feature_url'] = reverse('suite_toggle_featured', args=(suite.pk,))
                bundle.data['owner']['is_owner'] = True

        return bundle

    def hydrate(self, bundle):
        if 'num_stories' in bundle.data:
            del bundle.data['num_stories']
        if 'num_followers' in bundle.data:
            del bundle.data['num_followers']
        if 'main_image_url' in bundle.data:
            del bundle.data['main_image_url']
        if 'large_image_url' in bundle.data:
            del bundle.data['large_image_url']

        if 'owner' in bundle.data:
            del bundle.data['owner']

        return bundle

    def _process_hero_image(self, bundle):
        bundle = self.extract_resource_uri(bundle, 'hero_image')
        return bundle, False

    def obj_create(self, bundle, **kwargs):
        from django.utils.text import slugify
        from lib.utils import set_unique_suite_url
        from suites.tasks import fanout_new_suite, process_new_suite_member, process_new_suite
        bundle, post_process_image = self._process_hero_image(bundle)
        response = super(SuiteResource, self).obj_create(bundle, owner=bundle.request.user)

        # check to see if we need to change the slug to something other than
        # what the autoslug gives us.
        auto_slug = bundle.obj.slug
        ideal_slug = slugify(bundle.obj.name)
        if not auto_slug == ideal_slug:
            bundle.obj.slug = set_unique_suite_url(bundle.obj.owner, ideal_slug)
            bundle.obj.save()

        if post_process_image:
            resize_suite_hero_image.delay(bundle.obj.hero_image.pk)
        # if bundle.obj.hero_image:
        #     bundle.obj.hero_image.invalidate()

        try:
            process_new_suite(bundle.obj)
        except Exception as e:
            print(e)

        return response

    def obj_update(self, bundle, **kwargs):
        from lib.utils import check_suite_slug
        from suites.tasks import refresh_suite_stats, refresh_suite_featured_members

        bundle, post_process_image = self._process_hero_image(bundle)
        response = super(SuiteResource, self).obj_update(bundle, **kwargs)

        if post_process_image:
            resize_suite_hero_image.delay(bundle.obj.hero_image.pk)
            bundle.obj.cleanup_images()
        if bundle.obj.hero_image:
            bundle.obj.hero_image.invalidate()

        refresh_suite_featured_members(bundle.obj)
        refresh_suite_stats(bundle.obj)
        bundle.obj.invalidate()
        bundle.obj.owner.invalidate()
        return response

    def obj_delete(self, bundle, **kwargs):
        response = super(SuiteResource, self).obj_delete(bundle, **kwargs)
        bundle.obj.owner.invalidate()
        
        for story in bundle.obj.get_stories():
            story.invalidate()
        return response


class SuitePostAuthorization(Suite101BaseAuthorization):
    def update_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.member_of(bundle.obj.suite) or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.member_of(bundle.obj.suite) or \
                bundle.request.user.is_moderator


class SuitePostResource(Suite101Resource):
    suite = fields.ToOneField(SuiteResource, 'suite')
    # post = fields.ToOneField('articles.api.StoryResource', 'content_object')

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite_post'
        queryset = SuitePost.objects.all()
        authorization = SuitePostAuthorization()
        list_allowed_methods = ['get', 'post', 'patch']
        include_absolute_url = False
        always_return_data = True
        data_cache_key = 'suite:post'  
        cache_authed = False         

        fields = [
            'id'
        ]

        filtering = {
            'suite': 'exact',
            'content_type': 'exact',
            'object_id': 'exact'
        }

    def dehydrate(self, bundle):
        from articles.api import StoryMiniResource
        from links.api import LinkMiniResource

        if bundle.obj.content_type == ContentType.objects.get_for_model(Article):        
            resource = StoryMiniResource()
        elif bundle.obj.content_type == ContentType.objects.get_for_model(Link):        
            resource = LinkMiniResource()

        bundle.data = api_serialize_resource_obj(bundle.obj.content_object, resource, bundle.request)
        bundle.data['suite_id'] = bundle.obj.suite.id

        return bundle

    def obj_create(self, bundle, **kwargs):
        response = super(SuitePostResource, self).obj_create(bundle, **kwargs)
        bundle.obj.suite.invalidate()
        bundle.obj.content_object.invalidate()
        return response

    def obj_update(self, bundle, **kwargs):
        response = super(SuitePostResource, self).obj_update(bundle, **kwargs)
        if bundle.obj.suite:
            bundle.obj.suite.invalidate()
        bundle.obj.invalidate()
        return response

    def obj_delete(self, bundle, **kwargs):
        response = super(SuitePostResource, self).obj_delete(bundle, **kwargs)
        suite_story = bundle.obj
        duplicates = SuitePost.objects.filter(object_id=suite_post.object_id, suite_id=suite_post.suite.id)
        if duplicates and duplicates.count() > 0:
            duplicates.delete()
        if bundle.obj.suite:
            bundle.obj.suite.invalidate()
        if bundle.obj.content_object:
            bundle.obj.content_object.invalidate()
        return response


class SuiteInviteAuthorization(Suite101BaseAuthorization):
    def create_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

    def update_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

class SuiteInviteResource(Suite101Resource):
    suite = fields.ToOneField(SuiteMiniResource, 'suite')
    user_inviting = fields.ToOneField(UserMiniResource, 'user_inviting')
    user_invited = fields.ToOneField(UserMiniResource, 'user_invited', null=True)

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite_invite'
        queryset = SuiteInvite.objects.all()
        authorization = SuiteInviteAuthorization()
        validation = FormValidation(form_class=SuiteInviteForm)
        list_allowed_methods = ['get', 'post', 'patch', 'put']
        include_absolute_url = False
        always_return_data = True

        fields = [
            'id',
            'message',
            'status',
            'email',
            'email_invite'
        ]
        filtering = {
            'suite': ['exact'],
            'status': ['exact']
        }

    def dehydrate(self, bundle):   
        if bundle.obj.user_invited:
            bundle.data['user'] = api_serialize_resource_obj(bundle.obj.user_invited, UserMiniResource(), bundle.request)
        elif bundle.obj.email and bundle.obj.email_invite:
                bundle.data['user'] = json.dumps({
                    'email': bundle.obj.email, # email field
                    'by_email': bundle.obj.email_invite # boolean
                })
        else:
            raise Http404
      
        bundle.data['suiteId'] = bundle.obj.suite.pk
        bundle.data['invited'] = True

        return bundle

    def hydrate(self, bundle):
        User = get_user_model()
        if 'suite' in bundle.data:
            if isinstance(bundle.data['suite'], int) or bundle.data['suite'].isdigit():
                bundle.data['suite'] = get_object_from_pk(Suite, bundle.data['suite'], False)
            else:
                bundle = self.extract_resource_uri(bundle, 'suite')

        if 'user_invited' in bundle.data and bundle.data['user_invited']:
            bundle.data['user_invited'] = get_object_from_pk(User, bundle.data['user_invited'], False)                
        else:
            bundle.data['user_invited'] = None

        if 'user_inviting' in bundle.data:
            bundle.data['user_inviting'] = get_object_from_pk(User, bundle.request.user.pk, False)                

        if 'email' in bundle.data and bundle.data['email']:
            bundle.data['email_invite'] = True

        return bundle

    def obj_create(self, bundle, **kwargs):  
        from suites.tasks import fanout_suite_invite      
        try:
            response = super(SuiteInviteResource, self).obj_create(bundle, user_inviting=bundle.request.user)       
        except Exception as e:
            print(e)
        fanout_suite_invite.delay(bundle.obj)
        return response

    def obj_update(self, bundle, **kwargs):
        response = super(SuiteInviteResource, self).obj_update(bundle, **kwargs)
        if bundle.obj.status == SuiteInvite.STATUS.accepted:
            # the user is now a member of this suite
            SuiteMember.objects.get_or_create(
                suite=bundle.obj.suite,
                user=bundle.request.user
            )
            # user is now a member of the suite, auto follow.
            follow, created = Follow.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(bundle.obj.suite),
                object_id=bundle.obj.suite.pk,
                user=bundle.request.user
            )
    
            bundle.obj.suite.invalidate()
            bundle.request.user.invalidate()

        return response

    def obj_delete(self, bundle, **kwargs):
        response = super(SuiteInviteResource, self).obj_delete(bundle, **kwargs)

        if bundle.obj.suite:
            bundle.obj.suite.invalidate()
        return response


class SuiteRequestAuthorization(Suite101BaseAuthorization):
    def create_detail(self, object_list, bundle):
        return bundle.request.user.is_authenticated()

    def update_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

class SuiteRequestResource(Suite101Resource):
    suite = fields.ToOneField(SuiteMiniResource, 'suite')
    user = fields.ToOneField(UserMiniResource, 'user',)

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite_request'
        queryset = SuiteRequest.objects.all()
        authorization = SuiteRequestAuthorization()
        validation = FormValidation(form_class=SuiteRequestForm)
        list_allowed_methods = ['get', 'post', 'patch']
        include_absolute_url = False
        always_return_data = True

        fields = [
            'id',
            'message',
            'status'
        ]
        filtering = {
            'suite': ['exact'],
            'user': ['exact'],
            'status': ['exact']
        }

    def dehydrate(self, bundle):
        bundle.data['suiteId'] = bundle.obj.suite.pk
        bundle.data['user'] = api_serialize_resource_obj(bundle.obj.user, UserMiniResource(), bundle.request)
        bundle.data['requested'] = True

        return bundle

    def hydrate(self, bundle):
        bundle = self.extract_resource_uri(bundle, 'suite')
        bundle = self.extract_resource_uri(bundle, 'user')
        return bundle

    def obj_create(self, bundle, **kwargs):
        response = super(SuiteRequestResource, self).obj_create(bundle, user=bundle.request.user)
        return response

    def obj_update(self, bundle, **kwargs):
        from lib.utils import send_request_rejection_email

        response = super(SuiteRequestResource, self).obj_update(bundle, **kwargs)
        if bundle.obj.status == SuiteRequest.STATUS.accepted:
            SuiteMember.objects.get_or_create(
                suite=bundle.obj.suite,
                user=bundle.obj.user
            )
            # we also auto-follow this suite as a member
            Follow.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(bundle.obj.suite),
                object_id=bundle.obj.suite.pk,
                user=bundle.obj.user
            )

            bundle.obj.suite.invalidate()
            bundle.obj.user.invalidate()

        elif bundle.obj.status == SuiteRequest.STATUS.rejected:
            send_request_rejection_email(bundle.obj)

        return response

class SuiteMemberAuthorization(Suite101BaseAuthorization):
    def delete_detail(self, object_list, bundle):
        return bundle.obj.suite.is_editor(bundle.request.user.pk) or \
                bundle.request.user.is_moderator

class SuiteMemberResource(Suite101Resource):
    suite = fields.ToOneField(SuiteMiniResource, 'suite')
    user = fields.ToOneField(UserMiniResource, 'user')

    class Meta(Suite101Resource.Meta):
        resource_name = 'suite_member'
        queryset = SuiteMember.objects.all()
        authorization = SuiteMemberAuthorization()
        list_allowed_methods = ['get', 'post', 'patch', 'put']
        # detail_allowed_methods = ['delete']
        include_absolute_url = False
        always_return_data = True
        limit = 50

        fields = [
            'id',
            'status'
        ]

        filtering = {
            'suite': ['exact'],
            'user': ['exact']
        }

    def hydrate(self, bundle):
        bundle = self.extract_resource_uri(bundle, 'suite')
        bundle = self.extract_resource_uri(bundle, 'user')
        return bundle

    def dehydrate(self, bundle):
        try:
            bundle.data['suite_id'] = bundle.obj.suite.pk
            bundle.data['user_id'] = bundle.obj.user.pk
            bundle.data['member_id'] = bundle.obj.id
            bundle.data['user'] = api_serialize_resource_obj(bundle.obj.user, UserMiniResource(), bundle.request)
            bundle.data['member'] = True
            bundle.data['suite_editor'] = bundle.obj.suite.is_editor(bundle.obj.user.pk)
            bundle.data['owner'] = True if bundle.obj.suite.owner == bundle.obj.user else False
        except Exception as e:
            print(e)


        return bundle

    def obj_create(self, bundle, **kwargs):
        from suites.tasks import process_new_suite_member        
        response = super(SuiteMemberResource, self).obj_create(bundle, user=bundle.request.user)
        # hand off to task
        process_new_suite_member()
        return response

    def obj_update(self, bundle, **kwargs):
        from suites.tasks import process_suite_editor
        response = super(SuiteMemberResource, self).obj_update(bundle, **kwargs)

        if bundle.obj.suite.is_editor(bundle.obj.user.pk):
            try:
                process_suite_editor(bundle.obj)
            except Exception as e:
                print(e)
                pass
        return response

class SuiteSearchResource(Suite101SearchResource):
    class Meta:
        model = Suite
        queryset = Suite.objects.all()
        resource_name = 'suites'
        url_name = 'api_suite_search'

    # def get_default_queryset(self):
    #     return self._meta.model.objects.filter(owner__approved=True).order_by('-modified')

    def get_serialized_objs(self, request, obj_list): 
        try:
            objects = get_serialized_list(request, obj_list, 'suite:mini')
        except Exception as e:
            return []
        return objects

    def serialize_obj(self, obj):
        return api_serialize_resource_obj(obj, SuiteMiniResource(), HttpRequest())




