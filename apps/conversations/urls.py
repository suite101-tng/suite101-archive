from django.conf.urls import url
from moderation.views import ModFlagView
from django.views.generic.base import RedirectView
from .views import *

urlpatterns = [
	url(r'^$', RedirectView.as_view(url='/')),
	url(r'^(?P<hashed_id>[-_\w]+)$', ConversationDetailView.as_view(), name='conversation_detail'),

	# API FUNCTIONS
	url(r'^api/new_conv$', ConversationCreateView.as_view(), name='conv_create'),
	url(r'^api/post/flag$', ModFlagView.as_view(), kwargs={'type': 'post'}, name='flag_post'),
	url(r'^api/image_upload$', PostImageUploadView.as_view(), name='post_image_upload'),
	url(r'^api/media_embed$', PostMediaEmbedView.as_view(), name='post_media_embed'),
	url(r'^api/fetch_parent$', FetchConvParentView.as_view(), name='fetch_conv_parent'),
	url(r'^api/post/(?P<pk>[0-9]+)$', FetchSerializedPost.as_view(), name='fetch_serialized_post')	
	]
