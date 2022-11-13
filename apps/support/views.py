from __future__ import division
import datetime
import time
from django.views.generic.base import View
from lib.utils import get_client_ip, suite_render
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic import CreateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.contrib.contenttypes.models import ContentType
from lib.cache import get_object_from_pk, get_object_from_hash
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.conf import settings
from lib.utils import get_serialized_list, api_serialize_resource_obj  
from dateutil import parser
from .models import SupportQuestion, SupportCategory
from .api import SupportQuestionResource
from lib.enums import *

import json

class SupportEditCreateView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        response = super(SupportEditCreateView, self).dispatch(request, *args, **kwargs)
        return response 

    def post(self, request, *args, **kwargs):

        question_pk = request.POST.get('pk', '')
        create = True if request.POST.get('create', '') == 'true' else False
        toggle_publish = True if request.POST.get('togglepublish', '') == 'true' else False
        title = request.POST.get('title', '')
        answer = request.POST.get('answer', '')
        tags = request.POST.get('tags', '')
        
        if question_pk and not create:
            question = get_object_from_pk(SupportQuestion, question_pk, False)  
            if question:
                question.title = title
                question.answer = answer     
                if toggle_publish:
                    question.published = True if not question.published else False                

        elif create:
            question = SupportQuestion.objects.create(title=title, answer=answer, published=toggle_publish)

        if not question:
            raise Http404

        if tags:
            question.tags_list = tags

        question.save()
        question.invalidate()

        return HttpResponse('ok')

class SupportView(TemplateView, AjaxableResponseMixin):
    template_name = 'static/static_detail.html'
    static_type = 'support'

    def dispatch(self, *args, **kwargs):
        return super(SupportView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        innercontext = self.get_inner_context()
        return self.render_to_json_response(innercontext)

    def get_inner_context(self):
        innercontext = {}
        innercontext['viewType'] = self.static_type
        innercontext['questions'] = self.questions
        if self.request.user.is_authenticated() and self.request.user.is_moderator:
            innercontext['modViewing'] = True

        return innercontext

    def get(self, request, *args, **kwargs):
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.query = str(self.request.GET.get('q', ''))
        if self.query.find('?') > 0:
            self.query = self.query[:self.query.find('?')] # remove querystrings

        self.named_filter = str(self.request.GET.get('filter', ''))

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
        self.questions = pks = []
        results = []
        is_mod = True if request.user.is_authenticated() and request.user and request.user.is_moderator else False

        if not self.query:
            if is_mod and not self.named_filter == 'published':
                if not self.named_filter == 'draft':
                    pks = SupportQuestion.objects.all().values_list('pk', flat=True)[self.start:self.end]
                else:
                    pks = SupportQuestion.objects.filter(published=False).values_list('pk', flat=True)[self.start:self.end]
            else:
                pks = SupportQuestion.objects.filter(published=True).values_list('pk', flat=True)[self.start:self.end]

        else:
            from haystack.query import SearchQuerySet
            try:
                pks = SearchQuerySet().models(SupportQuestion).auto_query(self.query).values_list('pk', flat=True)[self.start:self.end]
            except Exception as e:
                pass            
            
        if pks:
            self.questions = get_serialized_list(request, pks, 'support:mini')
            if is_mod:
                for q in self.questions:
                    q['modViewing'] = True

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            return self.render_to_json_response({
                    "objects": self.questions
                }) 

        return super(SupportView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SupportView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()
        context['view_type'] = 'support'
        context['static_rendered'] = suite_render(self.request, 'support-shell', innercontext, False)
        return context
