from django.conf.urls import url
from .views import *

urlpatterns = [

    # API FUNCTIONS
    url(r'^api/route_event$', StatsEventRouter.as_view(), name='route_event'),    
    url(r'^api/beacon$', UnreadBeaconView.as_view(), name='unread_beacon'),
]