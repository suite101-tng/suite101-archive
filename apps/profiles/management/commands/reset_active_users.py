import datetime, time
from dateutil import parser
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lib.enums import SUITE_EPOCH
from articles.models import Article

class Command(BaseCommand):
    help = 'usage: python manage.py reset_active_users'

    def handle(self, *args, **options):
        User = get_user_model()

        # epoch = datetime.datetime.strptime(SUITE_EPOCH, "%Y-%m-%d").date()
        suite_epoch = parser.parse(SUITE_EPOCH)
        authors_of_new_stories = Article.objects.published().filter(author__is_active=True, created__gte=suite_epoch).values_list("author__pk", flat=True)

        users = User.objects.all().exclude(pk__in=list(authors_of_new_stories))
        for user in users:
            user.is_active = False
            user.save()
