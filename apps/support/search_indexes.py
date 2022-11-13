import json, time

from django.http import HttpRequest
from haystack import indexes, fields
from celery_haystack.indexes import CelerySearchIndex
from django.utils.html import strip_tags

from lib.enums import SEARCH_TYPE_STORY
from lib.utils import api_serialize_resource_obj, get_serialized_list
from .api import SupportQuestionResource
from .models import SupportQuestion


class SupportStorageField(fields.SearchField):
    '''
    extends SearchField class for storing a dict of values as a json string, and convert it back
    to an object when it's read
    '''
    def prepare(self, obj):
        return json.dumps(api_serialize_resource_obj(obj, SupportQuestionResource(), HttpRequest()))

    def convert(self, value):
        return json.loads(value)


class SupportIndexes(CelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, template_name='search/indexes/support/support_text.txt')
    obj_type = indexes.IntegerField()

    title = indexes.CharField(model_attr='title', boost=1.2)
    description = indexes.CharField(boost=1.1)
    tags = indexes.MultiValueField()
    # category = indexes.CharField(boost=1.05)

    # non-indexed, stored field
    stored_obj = SupportStorageField(indexed=False)

    def get_model(self):
        return SupportQuestion

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(published=True)

    def should_update(self, instance, **kwargs):
        if instance.published:
            return True
        self.remove_object(instance, **kwargs)
        return False

    def prepare_description(self, obj):
        try:
            description = strip_tags(bleach_filter(obj.answer, ['p']))
        except:
            description = ''
        return description

    def prepare_obj_type(self, obj):
        return SEARCH_TYPE_STORY

    def prepare_tags(self, obj):
        return [t for t in obj.tag_list]
