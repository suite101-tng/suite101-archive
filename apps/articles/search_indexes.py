import json, time

from django.http import HttpRequest
from haystack import indexes, fields
from celery_haystack.indexes import CelerySearchIndex

from lib.enums import SEARCH_TYPE_STORY
from lib.utils import api_serialize_resource_obj, get_serialized_list
from .api import StoryMiniResource
from .models import Article


class ArticleStorageField(fields.SearchField):
    '''
    extends SearchField class for storing a dict of values as a json string, and convert it back
    to an object when it's read
    '''
    def prepare(self, obj):
        return json.dumps(api_serialize_resource_obj(obj, StoryMiniResource(), HttpRequest()))

    def convert(self, value):
        return json.loads(value)


class ArticleIndexes(CelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    obj_type = indexes.IntegerField()

    title = indexes.CharField(model_attr='title', boost=1.5)
    suite_names = indexes.MultiValueField(boost=1.4)
    authorName = indexes.CharField(boost=1.3)
    excerpt = indexes.CharField(boost=1.2)

    date = indexes.DateField()    
    order = indexes.FloatField()
    tags = indexes.MultiValueField(boost=1.4)
    
    # non-indexed, stored field
    stored_obj = ArticleStorageField(indexed=False)

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.published().filter(author__pk=7444)

    def should_update(self, instance, **kwargs):
        if instance.author.approved and instance.author.is_active and instance.published:
            return True
        try:
            self.remove_object(instance, **kwargs)
        except:
            pass
        return False

    def prepare_author(self, obj):
        return obj.author.get_full_name()

    def prepare_order(self, obj):
        return time.mktime(obj.created.timetuple())

    def prepare_obj_type(self, obj):
        return SEARCH_TYPE_STORY

    def prepare_date(self, obj):
        return obj.created

    def prepare_suite_names(self, obj):
        try:
            return obj.get_story_suite_names()
        except Exception as e:
            print(e)
            return None

    def prepare_tags(self, obj):
        return [t for t in obj.tag_list]
