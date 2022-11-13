from django.conf.urls import url

from .views import *
from support.views import SupportEditCreateView
from stats.views import AdminStatsView

urlpatterns = [
    url(r'^$', AdminMonitorView.as_view(), name='admin_home'),
    url(r'^stats$', AdminStatsView.as_view(), name='admin_stats'),
    url(r'^members$', AdminMonitorView.as_view(), kwargs={'admin_type': 'members'}, name='admin_members'),
    url(r'^tags$', AdminMonitorView.as_view(), kwargs={'admin_type': 'tags'}, name='admin_tags'),
    url(r'^flags$', AdminMonitorView.as_view(), kwargs={'admin_type': 'flags'}, name='admin_flags'),
    url(r'^links$', AdminMonitorView.as_view(), kwargs={'admin_type': 'links'}, name='admin_monitor_links'),
    url(r'^stories$', AdminMonitorView.as_view(), kwargs={'admin_type': 'stories'}, name='admin_monitor_stories'),
    url(r'^suites$', AdminMonitorView.as_view(), kwargs={'admin_type': 'suites'}, name='admin_monitor_suites'),

    # API FUNCTIONS
    url(r'^api/support_edit$', SupportEditCreateView.as_view(), kwargs={}, name='support_edit'),
    url(r'^api/mod_card$', ModCardView.as_view(), name='mod_card'),
    url(r'^api/delete_spam$', ModDeleteSpammyView.as_view(), name='mod_del_spammy'),
    url(r'^mod/defer/(?P<pk>[0-9]+)$', ArticleDeferView.as_view(), name='article_defer_approval'),
    url(r'^api/flag_list$', GetModFlagListView.as_view(), name='mod_get_flag_list'),
    url(r'^api/clear_flag$', ModClearFlagView.as_view(), name='mod_clear_flag')
]