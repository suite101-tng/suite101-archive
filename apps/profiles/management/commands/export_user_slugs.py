import csv

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lib.utils import queryset_iterator



class Command(BaseCommand):
    help = 'usage: python manage.py export_user_slugs <file>'

    def handle(self, *args, **options):
        filename = args[0]

        users = queryset_iterator(get_user_model().objects.filter(is_active=True))
        with open(filename, 'wb') as csvfile:
            outfile = csv.writer(csvfile)
            for user in users:
                new_slug = '/%s' % user.slug
                outfile.writerow([user.slug, new_slug])