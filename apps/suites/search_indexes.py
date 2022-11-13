import json

from django.http import HttpRequest
from haystack import indexes, fields
from celery_haystack.indexes import CelerySearchIndex

from lib.enums import SEARCH_TYPE_SUITE
from lib.utils import api_serialize_resource_obj, get_serialized_list
from .api import SuiteMiniResource
from .models import Suite


class SuiteStorageField(fields.SearchField):
    '''
    extends SearchField class for storing a dict of values as a json string, and convert it back
    to an object when it's read
    '''
    def prepare(self, obj):
        try:
            return json.dumps(api_serialize_resource_obj(obj, SuiteMiniResource(), HttpRequest()))
        except Exception as e:
            print('failed to get a serialized (suite) object: %s' % e)
            return None


    def convert(self, value):
        return json.loads(value)


class SuiteIndexes(CelerySearchIndex, indexes.Indexable):
    obj_id = indexes.IntegerField(model_attr='pk')
    text = indexes.CharField(document=True, use_template=True)
    obj_type = indexes.IntegerField()

    # fields to boost.
    name = indexes.CharField(model_attr='name', boost=1.5)
    description = indexes.CharField(model_attr='description', boost=1.2)
    owner = indexes.CharField(boost=1.1)
    tags = indexes.MultiValueField(boost=1.4)
    order = indexes.IntegerField()

    modified = indexes.DateTimeField(model_attr='modified')

    # non-indexed, stored field
    stored_obj = SuiteStorageField(indexed=False)

    def get_model(self):
        return Suite

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(owner__pk=7444, owner__is_active=True, private=False)

    def should_update(self, instance, **kwargs):
        if instance.owner.approved and instance.owner.is_active:
            return True
        self.remove_object(instance, **kwargs)
        return False

    def prepare_order(self, obj):
        return obj.follower_count

    def prepare_tags(self, obj):
        return [t for t in obj.tag_list]

    def prepare_owner(self, obj):
        return obj.owner.get_full_name()

    def prepare_obj_type(self, obj):
        return SEARCH_TYPE_SUITE



