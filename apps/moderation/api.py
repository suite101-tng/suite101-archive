import datetime, time, json
from django.template.defaultfilters import truncatechars, date, wordcount, escape, timesince
from django.utils.html import strip_tags
from articles.templatetags.bleach_filter import bleach_filter
from django.conf.urls import url
from django.http import HttpRequest, Http404
from django.contrib.contenttypes.models import ContentType

from tastypie.resources import Resource
from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.validation import FormValidation, Validation
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.bundle import Bundle

from profiles.api import UserMiniResource
from articles.api import StoryMiniResource
from suites.api import SuiteMiniResource
from links.api import LinkMiniResource
from articles.models import Article
from suites.models import Suite
from links.models import Link

from moderation.models import ModNotes

from lib.utils import api_serialize_resource_obj, get_serialized_list
from lib.cache import get_object_from_pk
from django.contrib.auth import get_user_model

from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from .models import *

class ModeratorAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

    def read_detail(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

    def update_detail(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

    def delete_detail(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

class ModNoteResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'modnote_full'
        data_cache_key = 'modnote:full'         
        queryset = ModNotes.objects.all()
        authorization = ModeratorAuthorization()
        include_absolute_url = False
        always_return_data = True        

        fields = [
            'id'
        ]

        filtering = {
            'date': 'exact',
            'object_id': 'exact',
            'content_type': 'exact'
        }

    def dehydrate(self, bundle):
        note = bundle.obj
        bundle.data['created'] = time.mktime(note.date.timetuple())
        bundle.data['modNote'] = True 
        bundle.data['moderator'] = api_serialize_resource_obj(note.moderator, UserMiniResource, bundle.request)
        bundle.data['msg'] = note.message

        return bundle

    def get_object_list(self, request):
        return super(ModNoteResource, self).get_object_list(request)    

class FlagResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'flag_mini'
        data_cache_key = 'flag:mini'         
        queryset = Flag.objects.all()
        authorization = ModeratorAuthorization()
        include_absolute_url = False
        always_return_data = True        

        fields = [
            'id'
        ]

        filtering = {
            'created': 'exact',
            'object_id': 'exact',
            'content_type': 'exact'
        }

    def dehydrate(self, bundle):
        User = get_user_model()
        flag = bundle.obj

        resource = None
        if flag.content_type==ContentType.objects.get_for_model(User):
            resource = UserMiniResource()
            model = User
        elif flag.content_type==ContentType.objects.get_for_model(Link):
            resource = LinkMiniResource()
            model = Link            
        else:
            return None        

        try:
            flag_object = get_object_from_pk(model, flag.object_id, False)
        except Exception as e:
            print(e)

        bundle.data['object'] = api_serialize_resource_obj(flag_object, resource, bundle.request)
        bundle.data['created'] = time.mktime(flag.created.timetuple())
        bundle.data['message'] = bleach_filter(flag.message)

        bundle.data['reason'] = flag.reason
        bundle.data['cleared'] = flag.cleared
        bundle.data['user'] = api_serialize_resource_obj(flag.user, UserMiniResource, bundle.request)

        return bundle

    def get_object_list(self, request):
        return super(FlagResource, self).get_object_list(request) 