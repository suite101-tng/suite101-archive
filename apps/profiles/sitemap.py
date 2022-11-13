from django.contrib.sitemaps import Sitemap
from django.contrib.auth import get_user_model

class UserSitemap(Sitemap):
    limit = 10000
    changefreq = "weekly"
    priority = 0.5
    protocol = 'https'

    def items(self):
        User = get_user_model()
        return User.objects.filter(is_active=True, approved=True)

    def lastmod(self, obj):
        mod_dates = [obj.date_joined]

        if obj.suites.all():
            mod_dates.append(obj.member_suites.all().order_by('-modified')[0].modified)

        if obj.articles.all():
            mod_dates.append(obj.articles.all().order_by('-modified')[0].modified)

        mod_dates.sort(reverse=True)
        return mod_dates[0]