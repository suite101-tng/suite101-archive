from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
    
from notifications.views import NotificationsView
from profiles.views import UserAuthenticateView, FeedView, UserCreateView, UserDeleteView, UserSettingsView, UserRedirectView
from stats.views import UserStatsView
from support.views import SupportView
from lib.views import *
from moderation.views import AdminMonitorView
from lib.rss import *

from articles.sitemap import ArticleSitemap
from profiles.sitemap import UserSitemap
from suites.sitemap import SuiteSitemap
from project import settings
from django.conf.urls.static import static

# Tastypie
from tastypie.api import Api
from conversations.api import ConversationResource, PostResource, PostMiniResource
from links.api import LinkResource, LinkProviderResource
from articles.api import UserStorySearchResource, StoryResource, StoryImageResource, StoryMiniResource, StorySearchResource
from profiles.api import UserMiniResource, UserResource, UserSearchResource, UserEmailSearchResource
from suites.api import SuiteResource, SuiteMiniResource, SuitePostResource, SuiteImageResource
from suites.api import SuiteInviteResource, SuiteRequestResource, SuiteMemberResource, SuiteSearchResource
from support.api import SupportQuestionResource
from moderation.api import FlagResource

#### API ####
v1_api = Api(api_name='v1')

v1_api.register(StoryResource())
v1_api.register(StoryImageResource())
v1_api.register(StoryMiniResource())
v1_api.register(UserStorySearchResource())
v1_api.register(StorySearchResource())
v1_api.register(UserResource())
v1_api.register(UserMiniResource())
v1_api.register(UserSearchResource())
v1_api.register(UserEmailSearchResource())

v1_api.register(SuiteResource())
v1_api.register(SuiteMiniResource())
v1_api.register(SuitePostResource())
v1_api.register(SuiteImageResource())
v1_api.register(SuiteInviteResource())
v1_api.register(SuiteRequestResource())
v1_api.register(SuiteMemberResource())
v1_api.register(SuiteSearchResource())

v1_api.register(LinkResource())
v1_api.register(LinkProviderResource())
v1_api.register(FlagResource())
v1_api.register(SupportQuestionResource())

v1_api.register(ConversationResource())
v1_api.register(PostResource())
v1_api.register(PostMiniResource())


#### API ####


sitemaps = {
    'users': UserSitemap,
    'articles': ArticleSitemap,
    'suites': SuiteSitemap
}

handler400 = StaticView.as_view(static_type='error',error_type='404')
handler404 = StaticView.as_view(static_type='error',error_type='404')
handler500 = StaticView.as_view(static_type='error',error_type='500')

urlpatterns = [
    url(r'^$', FeedView.as_view(), name='home'),
    url(r'^a/', include('articles.urls')),
    url(r'^s/', include('suites.urls')),
    url(r'^c/', include('conversations.urls')),
    url(r'^u/', include('profiles.urls')),
    url(r'^l/', include('links.urls')),
    url(r'^lib/', include('lib.urls')),
    url(r'^admin$', AdminMonitorView.as_view(), name='admin_monitor'),
    url(r'^admin/', include('moderation.urls')),
    url(r'^x/', include('stats.urls')),
    url(r'^plurl/', include(admin.site.urls)),
    url(r'^api/', include(v1_api.urls)),
    url(r'^hijack/', include('hijack.urls')),
  
    # LOGIN/AUTH
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r'^login$', UserAuthenticateView.as_view(auth_type='login', auth_error=''), name='login'),
    url(r'^register$', UserAuthenticateView.as_view(auth_type='reg'), name='register'),
    url(r'^logout$', UserAuthenticateView.as_view(auth_type='logout'), name='logout'),
    
    url(r'^forgot$', UserAuthenticateView.as_view(auth_type='forgot'), name='forgot'),
    url(r'^reset/(?P<reset_key>[\w]+)$', UserAuthenticateView.as_view(auth_type='reset_with_key'), name='pw_reset_with_key'),

    url(r'^twitter/error$', TemplateView.as_view(template_name='profiles/twitter_error.html'), name='twitter_error'),
    # url(r'^register$', UserCreateView.as_view(), name='register'),
    url(r'^register/thanks$', TemplateView.as_view(template_name='emails/reset.html'), name='register_thanks'),
    
    # USER FEATURES
    url(r'^notifications$', NotificationsView.as_view(), name='notifications'),
    url(r'^stats$', UserStatsView.as_view(), name='stats'),
    url(r'^settings$', UserSettingsView.as_view(), name='user_settings'),

    # STATIC PAGES
    url(r'^about$', StaticView.as_view(static_type='about'), name='about'),
    url(r'^terms$', StaticView.as_view(static_type='terms'), name='terms'),
    url(r'^privacy$', StaticView.as_view(static_type='privacy'), name='privacy'),
    url(r'^rules$', StaticView.as_view(static_type='rules'), name='rules'),
    url(r'^ads$', StaticView.as_view(static_type='ads'), name='ads'),
    url(r'^royalties$', StaticView.as_view(static_type='royalties'), name='royalties'),
    url(r'^royalties/welcome$', StaticView.as_view(static_type='royal_welcome'), name='royal_welcome'),
    url(r'^welcome$', StaticView.as_view(static_type='welcome'), name='welcome'),
    url(r'^delete-me$', StaticView.as_view(static_type='close_account'), name='close_account'),
    url(r'^contact$', RedirectView.as_view(url='/about')),    
    url(r'^archived$', ArchiveView.as_view(), name='archived'),

    url(r'^support$', SupportView.as_view(), name='support'),    

    url(r'^400$', handler400),
    url(r'^404$', handler404),
    url(r'^500$', handler500),
    url(r'^maintenance$', TemplateView.as_view(template_name='static/errors/_maintenance.html'), name='error_503'),

    # EXPLORE
    url(r'^explore$', ExploreView.as_view(), kwargs={'feed_type': 'explore'}, name='explore'),
    url(r'^people$', ExploreView.as_view(), kwargs={'feed_type': 'people'}, name='explore_people'),
    url(r'^long$', ExploreView.as_view(), kwargs={'feed_type': 'long'}, name='explore_long'),    
    url(r'^latest$', ExploreView.as_view(), kwargs={'feed_type': 'latest'}, name='explore_latest'),
    url(r'^discussed$', ExploreView.as_view(), kwargs={'feed_type': 'discussed'}, name='explore_discussed_stories'),
    url(r'^suites$', ExploreView.as_view(), kwargs={'feed_type': 'suites'}, name='explore_suites'),

    # SEARCH
    # url(r'^q$', SearchView.as_view(), kwargs={'query': ''}, name='search'),
    url(r'^search$', RedirectView.as_view(url='/explore')),    
    # url(r'^q$', RedirectView.as_view(url='/explore')),    
    url(r'^q/(?P<query>[-_+\w]+)$', SearchView.as_view(), name='search'),

    # RSS FEEDS
    url(r'^rss$', RSSLatestArticleFeed(), name='featured_stories'),
    url(r'^rss/featured$', RSSLatestArticleFeed(), name='featured_stories_rss'),
    url(r'^(?P<slug>[-_\w]+)/rss$', RSSUserArticleFeed(), name='profile_feed_rss'),

    # MISC/admin
    url(r'^appstatus$', nginx_status, name='nginx_status'),
    url(r'^sitemap.xml', include('static_sitemaps.urls')),
    url(r'^decode/(?P<hashed_id>[-_\w]+)$', hash_decoder, name='hash_decoder'),
    url(r'^plurl$', RedirectView.as_view(url='/plurl/')),
    url(r'^popular$', RedirectView.as_view(url='/explore')), 
    url(r'^start$', RedirectView.as_view(url='/')),

    # USERS - ROOT SLUG MATCHERS
    url(r'^(?P<slug>[-_\w]+)$', slug_matcher, name='profile_detail'),   
    url(r'^(?P<slug>[-_\w]+)/suites$', slug_matcher, kwargs={'feed_type': 'suites'}, name='profile_detail_suites'),
    url(r'^(?P<slug>[-_\w]+)/posts$', slug_matcher, kwargs={'feed_type': 'posts'}, name='profile_detail_posts'),
    url(r'^(?P<slug>[-_\w]+)/followers$', slug_matcher, kwargs={'feed_type': 'followers'}, name='profile_detail_followers'),
    url(r'^(?P<slug>[-_\w]+)/following$', slug_matcher, kwargs={'feed_type': 'following'}, name='profile_detail_following'),
    url(r'^(?P<slug>[-_\w]+)/bio$', slug_matcher, kwargs={'feed_type': 'bio'}, name='profile_detail_bio'),
    url(r'^(?P<slug>[-_\w]+)/edit$', slug_matcher, kwargs={'edit_mode': True}, name='profile_edit'),
    # url(r'^(?P<author>[-_\w]+)/(?P<hashed_id>[-_\w]+)$', member_root_slug_matcher, name='story_detail'),
    url(r'^(?P<author>[-_\w]+)/(?P<hashed_id>[-_\w]+)$', member_root_slug_matcher, name='post_detail'),  

    url(r'^email$', TemplateView.as_view(template_name='emails/new_story_to_followers.html'), name='email_test')


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)