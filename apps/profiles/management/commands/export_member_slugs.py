import StringIO
import csv
from django.core.mail import EmailMessage   

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lib.utils import queryset_iterator

class Command(BaseCommand):
    help = 'usage: python manage.py export_user_slugs'

    def handle(self, *args, **options):

        # create a csv in memory
        csvfile = StringIO.StringIO()
        csvwriter = csv.writer(csvfile) 

        users = queryset_iterator(get_user_model().objects.filter(is_active=True))
        csvwriter.writerow(['uid', 'slug'])


        for user in users:
            print 'User %s' % user.pk

            csvwriter.writerow([
                user.pk,
                user.slug
            ])

        message = EmailMessage(
                    'Suite member slugs',
                    'CSV attached',
                    'dev@suite.io',
                    ['michael@suite.io']
                )
        message.attach('member_export.csv', csvfile.getvalue(), 'text/csv')
        message.send()