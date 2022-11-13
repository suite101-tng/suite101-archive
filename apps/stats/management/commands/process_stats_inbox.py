from django.core.management.base import BaseCommand
from stats.tasks import process_stats_inbox

class Command(BaseCommand):
    help = 'usage: python manage.py process_stats_inbox'

    def handle(self, *args, **options):
        try:
            process_stats_inbox()
        except Exception as e:
            print(e)
