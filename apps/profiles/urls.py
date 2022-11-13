from django.conf.urls import url
from django.views.generic.base import TemplateView

from moderation.views import ModFlagView
from .views import *


urlpatterns = [
    url(r'^(?P<pk>[0-9]+)/activation/resend$', UserReSendActivationView.as_view(), name='profile_resend_activation'),
    url(r'^(?P<pk>[0-9]+)/activate/(?P<activation_key>[\w]+)$', UserActivateView.as_view(), name='profile_activate'),
    url(r'^activated$', TemplateView.as_view(template_name='profiles/activated.html'), name='profile_activated'),

    # PASSWORD UPDATE
    url(r'^request_reset$', UserRequestResetView.as_view(), name='profile_request_reset'),
    url(r'^request_reset/thanks$', TemplateView.as_view(template_name='profiles/request_reset_thanks.html'), name='profile_request_reset_thanks'),
    


    url(r'^password/reset/thanks$', TemplateView.as_view(template_name='profiles/password_reset_thanks.html'), name='profile_password_reset_thanks'),
    url(r'^password/(?P<backend>[^/]+)/set$', UserPasswordSetView.as_view(), name='profile_set_password'),

    # EMAIL UPDATE
    url(r'^email/change$', UserEmailChangeView.as_view(), name='profile_update_email'),
    url(r'^(?P<pk>[0-9]+)/email_change/(?P<email_key>[\w]+)$', UserCompleteEmailChangeView.as_view(), name='profile_change_email'),
    url(r'^email/change/thanks$', TemplateView.as_view(template_name='profiles/email_change_thanks.html'), name='profile_email_changed_thanks'),
    url(r'^email/change/expired$', TemplateView.as_view(template_name='profiles/email_change_expired.html'), name='profile_email_change_expired'),

    # API FUNCTIONS
    
    # multi-purpose authenticate view (POST login, reg, reset, logout...)
    # url(r'^api/auth$', UserAuthenticateView.as_view(), name="auth_post"),

    url(r'^api/get_suites$', UserGetSuitesView.as_view(), name='api_get_suites'),
    url(r'^api/get_posts$', UserGetPostsView.as_view(), name='api_get_posts'),
    url(r'^api/get_people$', UserGetPeopleView.as_view(), name='api_get_people'),

    url(r'^api/user/(?P<pk>[0-9]+)$', GetUserFromPk.as_view(), name='api_get_user_from_pk'),
    url(r'^api/flag$', ModFlagView.as_view(), kwargs={'type': 'user'}, name='flag_user'),
    
    url(r'^api/password_change$', UserPasswordChangeView.as_view(), name='profile_update_password'),    
    
    url(r'^api/profile_img_upload$', UserUploadImageView.as_view(), name='profile_update_image'),
    url(r'^api/neighbours$', UserNeighbourSearch.as_view(), name='neighbour_search'),
    
    url(r'^api/deactivate$', UserDeactivateView.as_view(), name='user_deactivate'),
    url(r'^api/reactivate$', UserReactivateView.as_view(), name='user_reactivate'),

    url(r'^api/follow/(?P<pk>[0-9]+)$', UserFollowView.as_view(), name='user_follow'),
    url(r'^api/unfollow/(?P<pk>[0-9]+)$', UserUnFollowView.as_view(), name='user_unfollow'),
    url(r'^api/disconnect/(?P<backend>[^/]+)/$', social_disconnect, name='profile_social_disconnect'),
    url(r'^api/story_export/(?P<pk>[0-9]+)$', UserArticleDumpView.as_view(), name='story_export'),
    url(r'^api/contactable/(?P<pk>[0-9]+)$', UserContactableView.as_view(), name='user_contactable'),    
    url(r'^api/delete$', UserDeleteView.as_view(), name='profile_delete'),
    
    # registration/activation
    url(r'^sorry$', TemplateView.as_view(template_name='profiles/register_denied_blacklisted.html'), name='register_denied_blacklisted'),

 
]