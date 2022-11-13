import re, json, operator

from django.http import HttpRequest
from django.forms.models import ModelChoiceField
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.contrib.auth import get_user_model
from django.conf.urls import patterns, url, include
from django.db.models import Q, CharField, Value as V

from tastypie.resources import ModelResource
from tastypie.serializers import Serializer
from tastypie.authorization import Authorization
from tastypie.exceptions import Unauthorized
from tastypie.authentication import SessionAuthentication
from tastypie.cache import SimpleCache
from tastypie.validation import FormValidation
from haystack.query import SearchQuerySet

from lib.enums import DEFAULT_PAGE_SIZE
from lib.cache import get_object_from_pk
from lib.utils import api_serialize_resource_obj, get_serialized_list
from articles.models import Article
from links.models import Link
from suites.models import Suite
import json
import datetime
from time import mktime

class EncodeWithDatetime(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))
        return json.JSONEncoder.default(self, obj)

class CamelCaseJSONSerializer(Serializer):
    json_indent = 2
    formats = ['json']
    content_types = {
        'json': 'application/json',
    }

    def to_json(self, data, options=None):
        # Changes underscore_separated names to camelCase names to go from python convention to javacsript convention
        data = self.to_simple(data, options)

        def underscoreToCamel(match):
            return match.group()[0] + match.group()[2].upper()

        def camelize(data):
            if isinstance(data, dict):
                new_dict = {}
                for key, value in data.items():
                    new_key = re.sub(r"[a-z]_[a-z]", underscoreToCamel, key)
                    if isinstance(value, datetime.datetime):
                        value = int(mktime(value.timetuple()))
                    new_dict[new_key] = camelize(value)
                return new_dict
            if isinstance(data, (list, tuple)):
                for i in range(len(data)):
                    data[i] = camelize(data[i])
                return data
            return data

        camelized_data = camelize(data)

        return json.dumps(camelized_data, sort_keys=True)
        # return json.dumps(camelized_data, sort_keys=True, indent=self.json_indent)

    def from_json(self, content):
        # Changes camelCase names to underscore_separated names to go from javascript convention to python convention
        data = json.loads(content)

        def camelToUnderscore(match):
            return match.group()[0] + "_" + match.group()[1].lower()

        def underscorize(data):
            if isinstance(data, dict):
                new_dict = {}
                for key, value in data.items():
                    new_key = re.sub(r"[a-z][A-Z]", camelToUnderscore, key)
                    new_dict[new_key] = underscorize(value)
                return new_dict
            if isinstance(data, (list, tuple)):
                for i in range(len(data)):
                    data[i] = underscorize(data[i])
                return data
            return data

        underscored_data = underscorize(data)

        return underscored_data


class Suite101Authentication(SessionAuthentication):
    '''
    Authenticates everyone if the request is GET otherwise performs
    SessionAuthentication.
    '''
    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            return True
        return super(Suite101Authentication, self).is_authenticated(request, **kwargs)

    def get_identifier(self, request):
        from tastypie.compat import get_username_field
        if request.method == 'GET':
            return None
        return getattr(request.user, get_username_field())


class Suite101BaseAuthorization(Authorization):
    def create_detail(self, object_list, bundle):
        if bundle.request.user.is_active:
            return True
        raise Unauthorized("Sorry, your account is inactive")

    """ list create/update/delete not allowed (yet) """
    def create_list(self, object_list, bundle):
        raise Unauthorized("Sorry, no creates.")
    def delete_list(self, object_list, bundle):
        raise Unauthorized("Sorry, no deletes.")
    def update_list(self, object_list, bundle):
        raise Unauthorized("Sorry, no updates.")

    '''
    Authorizes every authenticated user to perform GET, for all others
    performs DjangoAuthorization.
    '''
    def is_authorized(self, request, object=None):
        if request.method == 'GET':
            return True
        else:
            return super(Suite101BaseAuthorization, self).is_authorized(request, object)


class Suite101Resource(ModelResource):
    """ Base Suite tastypie resource, we use this for base settings
        and for base invalidation of cached detail objects.
        TODO: caching list objects """

    class Meta:
        serializer = CamelCaseJSONSerializer()
        include_absolute_url = True
        include_resource_url = True
        data_cache_key = None
        cache_authed = True
        authentication = Suite101Authentication()

    def remove_api_resource_names(self, url_dict):
        """ remove request from the kwargs so our cachekeys don't break """
        kwargs_subset = url_dict.copy()
        try:
            del(kwargs_subset['request'])
        except KeyError:
            pass
        return super(Suite101Resource, self).remove_api_resource_names(kwargs_subset)

    def obj_update(self, bundle, **kwargs):
        response = super(Suite101Resource, self).obj_update(bundle, **kwargs)
        # try:
        #     bundle.obj.invalidate()
        # except:
        #     pass
        return response

    def obj_delete(self, bundle, **kwargs):
        response = super(Suite101Resource, self).obj_delete(bundle, **kwargs)
        return response

    def serialize(self, request, data, format, options=None):   
        if hasattr(data, 'obj'):      
            serialized_obj = super(Suite101Resource, self).serialize(request, data, format, options)      
            print(serialized_obj)
            return serialized_obj
        return super(Suite101Resource, self).serialize(request, data, format, options)        
           
    def serialize_list(self, model, object_tuples, resource, limit=None):
        json_objects = []
        for obj_tuple in object_tuples:
            model_obj = get_object_from_pk(model, obj_tuple[0], False)
            obj_json = api_serialize_resource_obj(model_obj, resource, HttpRequest())
            json_objects.append(obj_json)
            if limit and len(json_objects) == limit:
                break

        return json_objects

    def extract_resource_uri(self, bundle, field_name):
        if field_name in bundle.data and isinstance(bundle.data[field_name], dict):
            if 'resource_uri' in bundle.data[field_name]:
                bundle.data[field_name] = bundle.data[field_name]['resource_uri']
            if 'resourceUri' in bundle.data[field_name]:
                bundle.data[field_name] = bundle.data[field_name]['resourceUri']
        return bundle

class Suite101ModelFormValidation(FormValidation):
    """
    Override tastypie's standard ``FormValidation`` since this does not care
    about URI to PK conversion for ``ToOneField`` or ``ToManyField``.

    From https://github.com/toastdriven/django-tastypie/issues/152
    Take that same idea and extend it to allow for nested pks...
    But, only use this validation if we have a nested pk in a related model.
    Otherwise, just use the tastypie version (super)

    """

    def nested_pk_to_pk(self, nested_pk):
        if isinstance(nested_pk, dict):
            if 'pk' in nested_pk:
                return nested_pk['pk']
        return None

    def uri_to_pk(self, uri):
        slug = None
        if uri is None:
            return None

        pks = []

        # import pdb; pdb.set_trace()
        is_list = True
        if isinstance(uri, basestring):
            uri = [uri]
            is_list = False

        # assume it's a list now.
        for _uri in uri:
            if not _uri:
                continue
            if isinstance(_uri, dict):
                if 'id' in _uri:
                    pks.append(_uri['id'])
                    continue
                elif 'resource_uri' in _uri:
                    _uri = _uri['resource_uri']
                else:
                    raise ValueError("URI %s could not be converted to pk." % _uri)

            try:
                # hopefully /api/v1/<resource_name>/<slug>/
                # or /api/v1/<resource_name>/<pk>/
                resource_name = _uri.split('/')[3]
                identifier = _uri.split('/')[4]
            except (IndexError, ValueError):
                raise ValueError(
                    "URI %s could not be converted to pk." % _uri)

            if identifier:
                from articles.models import Article
                if resource_name == 'story':
                    klass = Article
                try:
                    if identifier.isdigit():
                        obj = klass.objects.get(pk=identifier)
                    else:
                        obj = klass.objects.get(slug__iexact=slug)
                except:
                    return None
                else:
                    pks.append(obj.pk)

        if not is_list and pks:
            return pks[0]
        return pks

    def is_valid(self, bundle, request=None):
        # import pdb; pdb.set_trace()
        data = bundle.data
        # Ensure we get a bound Form, regardless of the state of the bundle.
        if data is None:
            data = {}
        # copy data, so we don't modify the bundle
        data = data.copy()

        # convert URIs to PK integers for all relation fields
        relation_fields = [name for name, field in
                           self.form_class.base_fields.items()
                           if issubclass(field.__class__, ModelChoiceField)]

        converted = False
        for field in relation_fields:
            if field in data and data[field]:
                nested_pk = self.nested_pk_to_pk(data[field])
                if nested_pk:
                    converted = True
                    data[field] = nested_pk
                else:
                    converted = True
                    data[field] = self.uri_to_pk(data[field])

        if not converted:
            return super(Suite101ModelFormValidation, self).is_valid(bundle, request)

        # validate and return messages on error
        form = self.form_class(data)
        if form.is_valid():
            return {}
        return form.errors

class Suite101SearchResource(ModelResource):
    class Meta:
        serializer = CamelCaseJSONSerializer()
        # this must be overridden in subclass
        model = get_user_model()
        default_models = [get_user_model(), Article, Suite]
        queryset = get_user_model().objects.all()
        resource_name = 'user'
        url_name = 'api_user_search'

    def get_serialized_objs(self, request, obj_list): 
        try:
            objects = get_serialized_list(request, obj_list, 'story:mini')
        except Exception as e:
            return []
        return objects

    def do_search(self, request, *args, **kwargs):
        from haystack.query import SQ
        sqs = None
        start = kwargs.get('start', 0)
        end = kwargs.get('end', 15)
        query = kwargs.get('query', '')
        mlt = kwargs.get('mlt',False)
        exclude = kwargs.get('exclude',[])

        if query: 
            if mlt:
                query = [q for q in query.split(' ') if not q==""]
                sq = reduce(operator.__or__, [SQ(content=q) for q in query])                
                sqs = SearchQuerySet().filter(sq).exclude(id__in=list(exclude)).values_list('pk', flat=True)[:60]
                return sqs
            else:
                query = [q for q in query.split(' ') if not q==""]
                sq = reduce(operator.__or__, [SQ(content=q) for q in query])
                sqs = SearchQuerySet().models(self._meta.model).filter(sq).values_list('pk', flat=True)[start:end]
        # else:
        #     sqs = self.get_default_queryset()

        if not sqs:
            return []

        return self.get_serialized_objs(request, sqs)

    def _fetch_search_results(self, query, request):
        if query:
            return SearchQuerySet().models(self._meta.model).load_all().auto_query(query)
        else:
            return [], None
            