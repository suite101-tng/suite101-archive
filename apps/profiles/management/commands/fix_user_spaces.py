from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'usage: python manage.py fix_user_spaces'

    def handle(self, *args, **options):
    	User = get_user_model()
        for user in User.objects.all():
            user.first_name = '%s%s' % (user.first_name, ''.join(user.last_name.split(' ')[:1]))
            user.last_name = ''.join(user.last_name.split(' ')[1:])
            user.save()
