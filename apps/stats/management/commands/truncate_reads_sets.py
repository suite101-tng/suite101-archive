from django.core.management.base import BaseCommand
from stats.tasks import truncate_reads_sets

class Command(BaseCommand):
    help = 'usage: python manage.py truncate_reads_sets <set_type> <number_of_days> (choices are "stories", "suites"'
    def handle(self, *args, **options):
        try:
            set_type = str(args[0])
            days = int(args[1])
            truncate_reads_sets(set_type,days)
        except Exception as e:
            print(e)

