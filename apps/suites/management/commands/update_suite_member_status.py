from django.core.management.base import BaseCommand

from django.http import HttpRequest
from suites.models import SuiteMember, Suite
from lib.utils import queryset_iterator

class Command(BaseCommand):
    help = 'usage: python manage.py update_suite_member_status'

    def handle(self, *args, **options):

        # Update SuiteMember status
        suites = queryset_iterator(Suite.objects.all())
        for suite in suites:
            print suite.pk

            members = SuiteMember.objects.all().filter(suite=suite)
            for member in members:
                member.status = 'normal'
                member.save()

            # ensure owner is a member
            owner, created = SuiteMember.objects.get_or_create(suite=suite, user=suite.owner)
            owner.status = 'owner'
            owner.save()



