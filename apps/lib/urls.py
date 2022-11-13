from django.conf.urls import url
from .views import *

urlpatterns = [
 
    # API FUNCTIONS
    url(r'^api/top_tags$', FetchTrendingTags.as_view(), name='fetch_trending_tags'),    
    url(r'^api/notfound$', StaticView.as_view(static_type='notfound'), name='static_notfound')

]