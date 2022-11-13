from django.conf.urls import url
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from moderation.views import ModFlagView
from .views import *

urlpatterns = [
    url(r'^(?P<hashed_id>[-_\w]+)$', SuiteDetailView.as_view(), name='suite_detail'),
    url(r'^$', RedirectView.as_view(url='/suites', permanent=True)),

    # API FUNCTIONS
    
    url(r'^api/add_something/(?P<pk>[0-9]+)$', SuiteAddSomethingView.as_view(), name='suite_add_something'),    
    url(r'^api/image_upload$', SuiteImageUploadView.as_view(), name='suite_upload_image'),    
    url(r'^api/flag$', ModFlagView.as_view(), kwargs={'type': 'suite'}, name='flag_suite'),
    url(r'^api/follow/(?P<pk>[0-9]+)$', SuiteFollowView.as_view(), name='suite_follow'),
    url(r'^api/unfollow/(?P<pk>[0-9]+)$', SuiteUnFollowView.as_view(), name='suite_unfollow'),
    url(r'^api/new$', SuiteCreateView.as_view(), name='api_suite_create'),
    url(r'^api/suite_selector$', SuitesSelectorView.as_view(), name='add_to_suites'),
    url(r'^api/ask_to_join/(?P<pk>[0-9]+)$', SuiteJoinRequestView.as_view(), name='suite_join'),
    url(r'^api/request_action/(?P<pk>[0-9]+)$', SuiteJoinRequestRespondView.as_view(), name='suite_request_update'),
    url(r'^api/delete$', SuiteDeleteView.as_view(), name='suite_delete'),

]