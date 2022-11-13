import datetime, time, json
from django.template.defaultfilters import truncatechars, date, wordcount, escape, timesince
from django.utils.html import strip_tags
from django.conf.urls import url
from django.http import HttpRequest, Http404
from django.contrib.contenttypes.models import ContentType
from articles.templatetags.bleach_filter import bleach_filter

from tastypie.resources import Resource
from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.validation import FormValidation, Validation
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.bundle import Bundle

from profiles.api import UserMiniResource
from suites.api import SuiteMiniResource
from articles.models import Article, StoryParent
from suites.models import Suite, SuitePost
from lib.models import Follow
from moderation.api import ModNoteResource
from moderation.models import ModNotes

from lib.utils import api_serialize_resource_obj, get_serialized_list
from lib.cache import get_object_from_pk
from django.contrib.auth import get_user_model

from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from .models import *

class UserNotificationAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        return True if bundle.request.user == bundle.object.user else False

    def read_detail(self, object_list, bundle):
        return True if bundle.request.user == bundle.object.user else False

    def update_detail(self, object_list, bundle):
        return True if bundle.request.user == bundle.object.user else False

    def delete_detail(self, object_list, bundle):
        return True if bundle.request.user == bundle.object.user else False

class NotificationResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'notif_full'
        data_cache_key = 'notif:full'         
        queryset = Notification.objects.all()
        authorization = ReadOnlyAuthorization()
        include_absolute_url = False
        always_return_data = True        

        fields = [
            'id'
        ]

        filtering = {
            'date': 'exact',
            'verb': 'exact',
            'object_id': 'exact',
            'content_type': 'exact'
        }

    def dehydrate(self, bundle):
        User = get_user_model()
        notification = bundle.obj
        try:
            if notification.content_type == ContentType.objects.get_for_model(StoryParent):
                story = notification.content_object.content_object # the story posted in response
                parent = notification.content_object.story # the parent story
                bundle.data['object'] = { 'id': story.pk, 'absoluteUrl': story.get_absolute_url(), 'heading': story.get_heading()}
                bundle.data['target'] = { 'id': parent.pk, 'absoluteUrl': parent.get_absolute_url(), 'heading': parent.get_heading()}
                bundle.data['actor'] = { 'id': story.author.pk, 'absoluteUrl': story.author.get_absolute_url(), 'first_name': story.author.first_name, 'full_name': story.author.get_full_name(), 'main_image_url': story.author.get_profile_image()}
                bundle.data['responseType'] = True
                bundle.data['verb_verbose'] = 'posted a response to'
         
            elif notification.content_type == ContentType.objects.get_for_model(Follow):
                follow = notification.content_object
                followed_object = follow.content_object
                if follow.content_type == ContentType.objects.get_for_model(User):
                    bundle.data['object'] = api_serialize_resource_obj(follow.content_object, UserMiniResource(), bundle.request)
                    bundle.data['actor'] = { 'id': follow.user.pk, 'absoluteUrl': follow.user.get_absolute_url(), 'first_name': follow.user.first_name, 'full_name': follow.user.get_full_name(), 'main_image_url': follow.user.get_profile_image()}
                    bundle.data['followType'] = True
                    bundle.data['verb_verbose'] = 'is now following'

            elif notification.content_type == ContentType.objects.get_for_model(ModNotes):
                mod_note = notification.content_object
                target = mod_note.content_object
                if mod_note.content_type == ContentType.objects.get_for_model(User):
                    bundle.data['modNoteUser'] = True
                    target_json = { 'absoluteUrl': target.get_absolute_url(), 'first_name': target.first_name, 'full_name': target.get_full_name(), 'main_image_url': target.get_profile_image()}
                # right now, we asssume these are all users
                bundle.data['object'] = { 'id': mod_note.pk, 'message': truncatechars(bleach_filter(mod_note.message, ['p']), 200), 'created': time.mktime(mod_note.created.timetuple())} 
                bundle.data['target'] = target_json
                bundle.data['actor'] = { 'id': mod_note.moderator.pk, 'absoluteUrl': mod_note.moderator.get_absolute_url(), 'first_name': mod_note.moderator.first_name, 'full_name': mod_note.moderator.get_full_name(), 'main_image_url': mod_note.moderator.get_profile_image()}
                bundle.data['modNoteType'] = True
                bundle.data['verb_verbose'] = 'added a mod note about'

            elif str(notification.content_type) == str(ContentType.objects.get_for_model(SuitePost)):
                try:
                    from suites.utils import get_nearby_suite_posts
                    suite_post = notification.content_object
                    user = suite_post.added_by
                    post = suite_post.content_object
                    others = get_nearby_suite_posts(user, suite_post)
                    if others:
                        bundle.data['others'] = others.count()
                    bundle.data['object'] = api_serialize_resource_obj(suite_post.suite, SuiteMiniResource(), bundle.request)
                    bundle.data['actor'] = { 'id': user.pk, 'absoluteUrl': user.get_absolute_url(), 'first_name': user.first_name, 'full_name': user.get_full_name(), 'main_image_url': user.get_profile_image()}
                    bundle.data['target'] = { 'id': post.pk, 'absoluteUrl': post.get_absolute_url(), 'heading': post.get_heading()}
                    bundle.data['add_to_suite_type'] = True
                    bundle.data['verb_verbose'] = 'added'
                except Exception as e:
                    print('problem dehydrating suitepost: %s' % e)

            bundle.data['date'] = time.mktime(notification.date.timetuple())
            
            if notification.mod_type:
                bundle.data['mod_type'] = True

        except Exception as e:
            print(e)

        return bundle

    def get_object_list(self, request):
        return super(NotificationResource, self).get_object_list(request)    

class UserNotificationResource(Suite101Resource):
    ''' Always-fresh notification shell '''
    class Meta(Suite101Resource.Meta):
        resource_name = 'user_notif'
        data_cache_key = 'user:notif'         
        queryset = UserNotification.objects.all()
        authorization = ReadOnlyAuthorization()
        include_absolute_url = False
        always_return_data = True
        cache_authed = False

        fields = [
            'id'
        ]

        filtering = {
            'date': 'exact'
        }

    def dehydrate(self, bundle):
        user_notification = bundle.obj
        bundle.data = api_serialize_resource_obj(user_notification.notification, NotificationResource(), bundle.request)
        bundle.data['read'] = user_notification.read
        return bundle

    def get_object_list(self, request):
        return super(UserNotificationResource, self).get_object_list(request)