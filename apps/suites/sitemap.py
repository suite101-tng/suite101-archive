from django.contrib.sitemaps import Sitemap

from .models import Suite

class SuiteSitemap(Sitemap):
    limit = 10000
    changefreq = "daily"
    priority = 0.75
    protocol = 'https'

    def items(self):
        response = []
        suites = Suite.objects.filter(owner__approved=True, owner__is_active=True)
        return suites

    def lastmod(self, obj):
        mod_dates = [obj.modified]

        if obj.get_stories():
            mod_dates.append(obj.get_stories()[0].created)

        mod_dates.sort(reverse=True)
        return mod_dates[0]