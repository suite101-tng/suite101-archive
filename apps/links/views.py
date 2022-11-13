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
from .models import Link, LinkProvider
from .forms import *
from lib.enums import *
from stats.sets import *
import json


class LinkDetailView(AjaxableResponseMixin, CachedObjectMixin, DetailView):
    model = Link
    template_name = 'links/link_detail.html'
    obj = None

    def dispatch(self, request, *args, **kwargs):
        self.hashed_id = kwargs.get('hashed_id')
        self.obj = self.get_object()
        response = super(LinkDetailView, self).dispatch(request, *args, **kwargs)
        return response
  
    def get_reverse_url(self):
        url_name = 'link_detail'
        return self.obj.get_absolute_url()

    def get_object(self):
        try:
            self.obj = get_object_from_hash(self.hashed_id)
        except Exception as e:
            raise Http404
        return self.obj   

    def get(self, request, *args, **kwargs):
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        # if self.request.is_ajax():
        #     return self.render_to_json_response({
        #         "objects": None
        #     })

        return super(LinkDetailView, self).get(request, args, kwargs)

    def get_inner_context(self):
        from links.api import LinkResource
        innercontext = api_serialize_resource_obj(self.obj, LinkResource(), self.request)

        innercontext['userLoggedIn'] = self.request.user.is_authenticated()

        try:
            innercontext['suites'] = self.obj.get_suites(self.request)
            innercontext['num_suites'] = len(innercontext['suites'])
        except:
            pass

   
        # if self.page_num > 1:
        #     innercontext['currentPage'] = self.page_num     
        
        # try:
        #     innercontext['relatedTags'] = self.related_tags
        # except:
        #     pass

        return innercontext

    def get_context_data(self, **kwargs):
        import time
        from django.template.loader import render_to_string
        context = super(LinkDetailView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()

        has_page_param = self.request.GET.get('page')
        page_num = self.request.GET.get('page', '1')
        if not page_num.isdigit():
            raise Http404
        page_num = int(page_num)

        context['link_json_str'] = json.dumps(innercontext)
        context['object'] = self.object

        # json_ld = json.dumps({
        #     "@context":"http://schema.org",
        #     "@type":"CollectionPage",
        #     "name":"%s" % self.object.name,
        #     "description":"%s" % self.object.description or '',
        #     "url":"https://suite.io%s" % self.object.get_absolute_url(),
        #     "image": image,
        #     "editor": {
        #         "@type": "Person",
        #         "name": self.object.owner.get_full_name(),
        #         "sameAs":[ owner_facebook, owner_twitter ]
        #         },
        #     "lastReviewed": self.object.modified.strftime('%a %b %d %H:%M:%S +0000 %Y'), 
        #     "inLanguage":"en-us",
        #     "publisher": {
        #         "@type":"Organization",
        #         "name":"Suite",
        #         "logo":"",
        #         "sameAs":[ suite_facebook, suite_twitter ],
        #         "url":"https://suite.io",
        #         "founder":{"@type":"Person","name":"Michael Kedda"}
        #         },
        #     "location":{"@type":"PostalAddress","addressLocality":"Vancouver","addressRegion":"BC"}

        #     })
        # context['json_ld'] = json_ld


        context['title'] = innercontext['title']

        try:
            context['link_description'] = 'Posts about %s' % innercontext['title']
        except:
            context['link_description'] = '' 

        try:
            context['link_description'] += ' (From %s)' % innercontext['linkProvider'] 
        except:
            pass

        context['link_detail_rendered'] = suite_render(self.request, 'link-shell', innercontext)

        return context


class LinkProviderImageUpload(AjaxableResponseMixin, CachedObjectMixin, CreateView):
    form_class = ProviderImageUploadForm
    template_name = 'provider_icons/upload.html'  # doesn't get used.
    success_url = '/'  # doesn't get used.

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LinkProviderImageUpload, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        image = form.save(commit=False)
        # image.user = self.request.user
        image.save()

        return super(LinkProviderImageUpload, self).form_valid(form,
            extra_data={
                'image_url': image.image.url,
                'pk': image.pk
            }
        )
