from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model
from lib.utils import queryset_iterator
from articles.models import Article
from lib.cache import get_object_from_pk

class Command(BaseCommand):
    help = 'usage: python manage.py update_user_last_pub_date'

    def handle(self, *args, **options):
        User = get_user_model()
        users = queryset_iterator(User.objects.all())
        for user in users:
            try:
                print user.pk
                user.reset_last_published_date()
            except Exception as e:
                print(e)
                continue
     