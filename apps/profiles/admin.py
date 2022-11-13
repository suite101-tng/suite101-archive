from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'get_article_count')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'is_moderator')
    readonly_fields = (
        'last_login',
        'date_joined',
        'legacy_user_id',
        'profile_image',
        'twitter_connected',
        'last_known_ip',
    )
    exclude = (
        'password',
        'is_superuser',
        'user_permissions',
        'twitter_link_key',
        'activation_key',
        'reset_key',
        'reset_time',
        'new_email',
        'email_key',
        'email_change_time',
        'new_paypal_email',
        'paypal_email_key',
        'paypal_email_change_time',
        'facebook_connected',
    )

    def get_article_count(self, obj):
        return '%s' % obj.articles.published().count()


admin.site.register(User, UserAdmin)