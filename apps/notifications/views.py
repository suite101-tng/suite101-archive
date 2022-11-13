import os
import logging
import datetime
import json
import collections
from random import randint, randrange
log = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.template import loader, Context
from django.views.generic import CreateView
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import patch_cache_control
from django.contrib.auth.decorators import user_passes_test

from project import settings
from suites.models import Suite
from articles.models import Article
from lib.enums import DEFAULT_PAGE_SIZE
from lib.decorators import ajax_login_required
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.models import Follow
from lib.cache import get_object_from_hash, get_object_from_pk, get_object_from_slug
from lib.utils import api_serialize_resource_obj, suite_render, get_serialized_list
from articles.api import StoryMiniResource
from profiles.forms import UserCreateForm
from profiles.api import UserMiniResource

class NotificationsView(AjaxableResponseMixin, TemplateView):
    template_name = 'profiles/notifications_detail.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(NotificationsView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from notifications.tasks import clear_unread_notifications
        if not request.user and request.user.is_authenticated():
            raise Http404

        clear_this_notif = request.POST.get('clearnotif', False)
        if clear_this_notif:
            print('----------- we should be clearing just this one notif')

        clear_all_notifs = request.POST.get('readem', False)
        if clear_all_notifs:
            clear_unread_notifications(request.user)            

        # TODO: return fresh counts
        return HttpResponse('ok')

    def get(self, request, *args, **kwargs):
        from django.template.loader import render_to_string

        try:
            self.page_num = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page_num = 1

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = True 

        self.next_page_num = self.page_num + 1
        self.prev_page_num = self.page_num - 1 if self.has_previous else 0    

        self.notif_filter = request.GET.get('feedtype', None)
        key_lifespan = 300 # five minutes
        self.notifs = []
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        self.notifs = request.user.get_my_notifications(request, notif_filter=self.notif_filter)[self.start:self.end]
        
        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        if self.request.is_ajax():
            if not self.notifs:
                raise Http404
            return self.render_to_json_response({
                    "objects": self.notifs
                })            
  
        return super(NotificationsView, self).get(request, *args, **kwargs)

    def get_inner_context(self):
        innercontext = {}
        innercontext['title'] = 'My Notifications'
        innercontext['prevPage'] = self.prev_page_num
        innercontext['nextPage'] = self.next_page_num
        innercontext['isMod'] = True if self.request.user.is_moderator else False
        
        if self.page_num > 1:
            innercontext['currentPage'] = self.page_num     

        innercontext['notifs'] = self.notifs
        if not self.notif_filter or self.notif_filter == 'all':
            innercontext['allFilter'] = True
        else:
            innercontext['%sFilter' % self.notif_filter] = True

        return innercontext

    def get_context_data(self, **kwargs):
        context = super(NotificationsView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context();
        context['notifs_rendered'] = suite_render(self.request, 'notifications-detail', innercontext)
        return context     