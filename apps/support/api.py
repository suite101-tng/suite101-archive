import datetime, time, json
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
from articles.templatetags.bleach_filter import bleach_filter

from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from .models import SupportQuestion, SupportCategory

class SupportAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        if not bundle.obj.published:
            return False if not request.user.is_moderator else True
        return True

    def read_detail(self, object_list, bundle):
        if not bundle.obj.published:
            return False if not request.user.is_moderator else True
        return True

    def update_detail(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

    def delete_detail(self, object_list, bundle):
        return True if bundle.request.user.is_moderator else False

class SupportQuestionResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'support_mini'
        data_cache_key = 'support:mini'         
        queryset = SupportQuestion.objects.all()
        authorization = SupportAuthorization()
        include_absolute_url = False

        fields = [
            'id'
        ]

        filtering = {
        }

    def dehydrate(self, bundle):
        question = bundle.obj

        bundle.data['title'] = question.title if question.title and not question.title == 'Untitled' else None
        bundle.data['answer'] = bleach_filter(question.answer)
        bundle.data['published'] = True if question.published else False
        bundle.data['answer_excerpt'] = truncatechars(bleach_filter(question.answer, ['p']), 200)

        if question.category:
            bundle.data['category'] = {
                'title': question.category.title,
                'description': question.category.description
                }

        tags = []
        if question.tag_list:
            try:
                tags = json.loads(question.tag_list)
                if tags:
                    tags_obj = [{'tag': '%s' % tag, 'tagUrl': '/q/%s' % (re.sub('[^0-9a-zA-Z]+', '-', tag).lower())} for tag in tags]
                    bundle.data['tag_list'] = tags_obj
            except Exception as e:
                pass

        return bundle

    def get_object_list(self, request):
        return super(SupportQuestionResource, self).get_object_list(request)