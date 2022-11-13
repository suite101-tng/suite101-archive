from django.contrib import admin
from .models import Suite


class SuiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'show_url', 'num_stories', 'owner', 'created', 'featured')
    search_fields = ('name', 'owner', 'description')
    raw_id_fields = ('owner', )

    def show_url(self, instance):
        return '<a href="%s" target="_blank">View on site</a>' % (instance.get_absolute_url())
    show_url.allow_tags = True

    def num_stories(self, instance):
        return 99

admin.site.register(Suite, SuiteAdmin)