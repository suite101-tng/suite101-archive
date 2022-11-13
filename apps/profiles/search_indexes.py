import json

from django.http import HttpRequest
from haystack import indexes, fields
from celery_haystack.indexes import CelerySearchIndex

from lib.enums import SEARCH_TYPE_USER
from django.contrib.auth import get_user_model
from profiles.api import UserMiniResource
from lib.utils import api_serialize_resource_obj, get_serialized_list

class SuiteUserStorageField(fields.SearchField):
    '''
    extends SearchField class for storing a dict of values as a json string, and convert it back
    to an object when it's read
    '''
    def prepare(self, obj):
        return json.dumps(api_serialize_resource_obj(obj, UserMiniResource(), HttpRequest()))
        # objects = json.dumps(get_serialized_list(HttpRequest(), obj.pk, "user:mini"))
        # return objects if objects else None

    def convert(self, value):
        return json.loads(value)

class SuiteUserIndexes(CelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    obj_type = indexes.IntegerField()
    order = indexes.IntegerField()

    # fields to boost.
    name = indexes.CharField(boost=1.5)
    by_line = indexes.CharField(model_attr='by_line', boost=1.3)
    tags = indexes.MultiValueField(boost=1.4)

    # non-indexed, stored field
    stored_obj = SuiteUserStorageField(indexed=False)

    def get_model(self):
        return get_user_model()

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(approved=True, is_active=True)

    def should_update(self, instance, **kwargs):
        if instance.approved and instance.is_active:
            return True
        self.remove_object(instance, **kwargs)
        return False

    def prepare_order(self, obj):
        return obj.followers_count

    def prepare_tags(self, obj):
        return [t for t in obj.tag_list]

    def prepare_obj_type(self, obj):
        return SEARCH_TYPE_USER

    def prepare(self, obj):
        return super(SuiteUserIndexes, self).prepare(obj)
