import json, time

from django.http import HttpRequest
from haystack import indexes, fields
from celery_haystack.indexes import CelerySearchIndex

from lib.enums import SEARCH_TYPE_LINK
from lib.utils import api_serialize_resource_obj, get_serialized_list
from .api import LinkMiniResource
from .models import Link


class LinkStorageField(fields.SearchField):
    '''
    extends SearchField class for storing a dict of values as a json string, and convert it back
    to an object when it's read
    '''
    def prepare(self, obj):
        return json.dumps(api_serialize_resource_obj(obj, LinkMiniResource(), HttpRequest()))

    def convert(self, value):
        return json.loads(value)


class LinkIndexes(CelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    obj_type = indexes.IntegerField()

    title = indexes.CharField(boost=1.1)
    description = indexes.CharField(boost=1.05)
    suite_names = indexes.MultiValueField(boost=1.05)
    provider = indexes.CharField(boost=1.05)
    # tags = indexes.MultiValueField(boost=1.4)

    # non-indexed, stored field
    stored_obj = LinkStorageField(indexed=False)

    def get_model(self):
        return Link

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.exclude(provider__status='banned')

    def should_update(self, instance, **kwargs):
        if not instance.provider.banned:
            return True
        self.remove_object(instance, **kwargs)
        return False

    def prepare_title(self, obj):
        embed = json.loads(obj.oembed_string)
        try:
            return embed['title']
        except:
            title = ''
        return title

    def prepare_description(self, obj):
        embed = json.loads(obj.oembed_string)
        try:
            description = embed['description']
        except:
            description = ''
        return description

    def prepare_provider(self, obj):
        return obj.provider.name

    def prepare_obj_type(self, obj):
        return SEARCH_TYPE_LINK

    def prepare_date(self, obj):
        return obj.created

    def prepare_suite_names(self, obj):
        try:
            return obj.get_suite_names()
        except Exception as e:
            print(e)
            return None

    # def prepare_tags(self, obj):
    #     return [t for t in obj.tag_list]
