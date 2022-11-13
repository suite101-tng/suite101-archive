from django.contrib import admin
from .models import Article


class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_name', 'status', 'created', 'modified']
    search_fields = ['title']
    readonly_fields = [
        'author',
        'body_length',
    ]

    def author_name(self, obj):
        return obj.author.get_full_name()

admin.site.register(Article, ArticleAdmin)
