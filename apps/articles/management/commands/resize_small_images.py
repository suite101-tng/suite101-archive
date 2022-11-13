from django.core.management.base import BaseCommand

from articles.models import ArticleImage
from lib.utils import resize_story_image, queryset_iterator


class Command(BaseCommand):
    help = 'usage: python manage.py resize_small_images'

    def handle(self, *args, **options):

        for image_object in queryset_iterator(ArticleImage.objects.all()):
            if image_object.image.width > 299 and image_object.image.width < 720:
                try:
                    resize_story_image(image_object, True, 'article', True)
                    if image_object.article.get_images().filter(is_main_image=True).count() > 1:
                        image_object.article.get_images().filter(is_main_image=True).exclude(pk=image_object.pk).delete()
                        image_object.article.invalidate()
                except Exception as e:
                    print(e)
                    continue
