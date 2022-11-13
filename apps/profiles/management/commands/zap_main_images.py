from django.core.management.base import BaseCommand
from lib.utils import queryset_iterator
from articles.models import *

class Command(BaseCommand):
    help = 'usage: python manage.py zap_main_images'

    def handle(self, *args, **options):

    	ArticleImage.objects.filter(is_main_image=True).update(is_main_image=False)

		# images = ArticleImage.objects.filter(is_main_image=True)
		# for image in images: 
		# 	is_main_image = False
		# 	image.save()
