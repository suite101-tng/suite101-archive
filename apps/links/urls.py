from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^(?P<hashed_id>[-_\w]+)$', LinkDetailView.as_view(), name='link_detail'),

    # upload provider image
    url(r'^api/upload_provider_image$', LinkProviderImageUpload.as_view(), name='upload_provider_image'),
]
