import datetime
import time
from django.template.defaultfilters import truncatechars, date, wordcount, escape, timesince
from django.utils.html import strip_tags
from django.conf.urls import url
from django.http import HttpRequest, Http404
from django.contrib.contenttypes.models import ContentType

from tastypie.resources import Resource
from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.validation import FormValidation, Validation
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.bundle import Bundle

from lib.utils import api_serialize_resource_obj, get_serialized_list
from lib.cache import get_object_from_pk
from django.contrib.auth import get_user_model
from .utils import fetch_oembed_data
import json

from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from .models import Link, LinkProvider

class LinkAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        # return object_list.filter(status=Link.STATUS.published)
        return True

    def read_detail(self, object_list, bundle):
        return True

    def update_detail(self, object_list, bundle):
        return True

    def delete_detail(self, object_list, bundle):
        return True

class LinkMiniResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'link_mini'
        data_cache_key = 'link:mini'         
        queryset = Link.objects.all()
        authorization = ReadOnlyAuthorization()

        fields = [
            'id'
        ]

        filtering = {
            'status': 'exact',
            'provider': ALL_WITH_RELATIONS
        }

    def dehydrate(self, bundle):
        link = bundle.obj
        try:
            embed = json.loads(link.oembed_string)
        except:
            fresh_oembed_data, normalized_url, media_type = fetch_oembed_data(link.link)
            link.oembed_string = json.dumps(fresh_oembed_data)
            link.media_type = media_type
            link.invalidate()
            link.save()

        # core fields
        bundle.data['link_resource_uri'] = LinkResource().get_resource_uri(link)
        bundle.data['hash'] = link.hashed_id
        bundle.data['obj_type'] = 'link'
        bundle.data['link_type'] = True
        bundle.data['ctype'] = ContentType.objects.get_for_model(link)
        bundle.data['absolute_url'] = link.get_absolute_url()
        bundle.data['provider'] = api_serialize_resource_obj(link.provider, LinkProviderResource(), bundle.request)

        # bundle.data['num_responses'] = len(link.get_response_pks()) or 0

        try:
            bundle.data['html_object'] = embed['media']['html']
        except:
            try:
                bundle.data['html_object'] = embed['html']
            except:
                pass

        try:
            bundle.data['description'] = embed['description']
        except:
            pass

        try:
            bundle.data['title'] = embed['title']
        except:
            pass

        return bundle

    def get_object_list(self, request):
        return super(LinkMiniResource, self).get_object_list(request)


class LinkResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'link'
        data_cache_key = 'link:full'        
        cache_authed = True               
        queryset = Link.objects.filter()
        authorization = LinkAuthorization()
        always_return_data = True
        list_allowed_methods = ['post', 'get']
        detail_allowed_methods = ['get', 'delete', 'patch']

        fields = [
            'id',
            'title'
        ]

        filtering = {
            'object_id': 'exact',
            'content_type': 'exact',
        }

    def dehydrate(self, bundle):
        try:
            link = bundle.obj
            embed = json.loads(link.oembed_string)

            # core fields
            bundle.data['link_resource_uri'] = self.get_resource_uri(link)
            bundle.data['hash'] = link.get_hashed_id()
            bundle.data['obj_type'] = 'link'
            bundle.data['link'] = True
            bundle.data['absolute_url'] = link.get_absolute_url()

            bundle.data['provider'] = api_serialize_resource_obj(link.provider, LinkProviderResource(), bundle.request)

            try:
                bundle.data['html_object'] = embed['media']['html']
            except:
                pass

            try:
                bundle.data['description'] = embed['description']
            except:
                pass

            try:
                bundle.data['title'] = embed['title']
            except:
                pass

            try:
                bundle.data['tags'] = json.loads(str(link.tag_list))
            except:
                pass

            try:
                responses, response_auths = link.get_published_children(bundle.request)
                bundle.data['responses'] = responses
                bundle.data['response_auths'] = response_auths
                bundle.data['num_responses'] = len(responses) or 0
            except Exception as e:
                print(e)

        except Exception as e:
            print(e)

        return bundle

    def hydrate(self, bundle):
        # if 'owner' in bundle.data:
        #     del bundle.data['owner']

        return bundle


class LinkProviderResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'link_provider'
        data_cache_key = 'provider:mini'    
        queryset = LinkProvider.objects.all()
        list_allowed_methods = ['post', 'get']
        include_absolute_url = False
        authorization = ReadOnlyAuthorization()            

        fields = [
            'id'
        ]

        filtering = {
        }

    def dehydrate(self, bundle):
        provider = bundle.obj

        bundle.data['id'] = provider.pk
        bundle.data['name'] = provider.name
        bundle.data['link'] = provider.link

        try:
            bundle.data['image_url'] = provider.image.image.url
        except:
            pass

        return bundle

    def get_object_list(self, request):
        return super(LinkProviderResource, self).get_object_list(request)