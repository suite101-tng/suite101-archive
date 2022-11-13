import datetime
import logging
import json
log = logging.getLogger(__name__)
from random import randrange, uniform
from functools import wraps

from django.views.generic import CreateView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, DeleteView, FormView
from django.views.generic.base import View
from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import patch_cache_control, never_cache
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import available_attrs
from django.contrib.contenttypes.models import ContentType

from project import settings
from lib.enums import *
from articles.models import Article, StoryParent, StoryEmbed
from suites.models import Suite, SuitePost
from articles.forms import *
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.cache import get_object_from_pk, get_object_from_slug, get_object_from_hash
from lib.utils import api_serialize_resource_obj, suite_render, get_serialized_list, strip_non_ascii
from lib.views import GenericFollowView, GenericUnFollowView
from .api import StoryMiniResource, StoryEmbedResource
from .forms import ArticleUploadImageForm

class StoryDetailView(AjaxableResponseMixin, CachedObjectMixin, DetailView):
    model = Article
    showing_archive = False
    template_name = 'stories/story_detail.html'
    article = None

    def dispatch(self, *args, **kwargs):
        if not self.article:
            raise Http404

        response = super(StoryDetailView, self).dispatch(*args, **kwargs)
        return response

    def get_reverse_url(self):
        url_name = 'story_detail'
        # return reverse(url_name, kwargs={'hashed_id': self.object.hashed_id})
        return self.article.get_absolute_url()

    def get_object(self, queryset=None):
        article = Article.objects.all().select_related('author')
        # User is inactive
        if not self.article.author.is_active and not self.request.user == self.article.author and not self.request.user.is_staff:
            raise Http404
        else:
            if self.article and not self.article.published:
                #deleted article...
                if self.article.status == Article.STATUS.deleted:
                    raise Http404
                else:
                    # drafts... only staff and owners can see.
                    if not self.request.user == self.article.author and not self.request.user.is_staff:
                        raise Http404

        return self.article

    def get(self, request, *args, **kwargs):
        self.page_num = None
        return super(StoryDetailView, self).get(request, args, kwargs)

    def get_inner_context(self):
        from articles.api import StoryResource        
        innercontext = api_serialize_resource_obj(self.object, StoryResource(), self.request)
        return innercontext

    def get_context_data(self, **kwargs):
        from lib.utils import get_client_ip
        try:
            context = super(StoryDetailView, self).get_context_data(**kwargs)
            innercontext = self.get_inner_context()
            story = self.object

            context['meta_robots'] = '%s, follow, noodp, noydir' % ('index' if story.is_indexed() else 'noindex')
            context['canonical_link'] = url = '%s%s' % (settings.SITE_URL, story.get_absolute_url())
            context['json_ld'] = story.get_jsonld(self.request)

            if self.page_num:
                context['meta_robots'] = 'noindex, follow, noodp, noydir'

            context['title'] = innercontext['title']   
            try:
                context['description'] = innercontext['subtitle'] if innercontext['subtitle'] else innercontext['body_excerpt_no_tags']
            except:
                context['description'] = ''

            context['initial_referrer'] = strip_non_ascii(self.request.META.get('HTTP_REFERER', ''))
            context['ip_address'] = get_client_ip(self.request)

            context['story_json_str'] = json.dumps(innercontext)
            context['story_detail_rendered'] = suite_render(self.request, 'story-detail', innercontext)
        except Exception as e:
            print('problem getting context: %s' % e)
        return context