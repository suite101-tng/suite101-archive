from django.core.management.base import BaseCommand

from suites.models import Suite
from lib.tasks import resize_suite_hero_image

class Command(BaseCommand):
    help = 'usage: python manage.py convert_suite_images'

    def handle(self, *args, **options):
        for suite in Suite.objects.filter(images__isnull=False):
            suite.hero_image = suite.images.all()[0]
            resize_suite_hero_image.delay(suite.hero_image.pk)
            suite.save()
            suite.cleanup_images()
