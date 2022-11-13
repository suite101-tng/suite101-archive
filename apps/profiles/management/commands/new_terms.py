from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lib.utils import queryset_iterator

class Command(BaseCommand):
    help = 'usage: python manage.py new_terms'

    def handle(self, *args, **options):

        users = queryset_iterator(get_user_model().objects.all())
        for user in users:
        	user.accepted_terms = False
        	user.save()
