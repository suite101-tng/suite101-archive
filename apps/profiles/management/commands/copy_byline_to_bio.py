from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model
from django.db.models import F

class Command(BaseCommand):
    help = 'usage: python manage.py fix_user_images'

    def handle(self, *args, **options):
    	User = get_user_model()
        User.objects.update(bio=F('by_line'))
        User.objects.update(by_line='')