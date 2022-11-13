from django.core.management.base import NoArgsCommand

from django.core import management
from haystack import connections


class Command(NoArgsCommand):
    help = 'usage: python manage.py rebuild_elasticsearch'

    def handle_noargs(self, **options):
        backend = connections['default'].get_backend()
        backend.setup_complete = False
        backend.existing_mapping = None
        management.call_command('rebuild_index', interactive=False, verbosity=1)
