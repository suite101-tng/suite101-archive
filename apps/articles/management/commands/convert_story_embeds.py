from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup as soup
import re
from django.contrib.contenttypes.models import ContentType
from articles.models import Article, ArticleImage, StoryEmbed


class Command(BaseCommand):
    help = 'usage: python manage.py convert_story_embeds'

    def handle(self, *args, **options):
        # stories = Article.objects.published().filter(author__pk=7444)
    
        stories = Article.objects.published().filter(pk=216875)
        embed_pk = 116

        image_string = 'data-type="image"'
        for story in stories.iterator():
            try:
                html = soup(story.body.content, "html5lib")
                figures = html.findAll('figure')
                figs = [fig for fig in figures]
                if figs:
                    # data-id="188449"
                    for fig in figs:
                        try:
                            fig_id = re.findall(r'data-id="([^"]*)"', str(fig))[0]
                            # if fig_id:
                            #     print 'we have a fig id: %s' % fig_id
                            #     fig_id = fig_id[0]
                            #     try:
                            #         image = ArticleImage.objects.get(pk=fig_id)
                            #     except:
                            #         image = None
                            #     if image:
                            #         story_embed = StoryEmbed.objects.create(story=story, object_id=fig_id, content_type=ContentType.objects.get_for_model(ArticleImage))       
                            #         embed_pk = story_embed.pk                     
                            #         print 'we have a new story_embed object: %s' % embed_pk
                            #     else:
                            #         embed_pk = fig_id
                        except Exception as e:
                            print('nope: %s' % e)
                            # continue

                        new_embed_attrs = 'data-id="%s" data-type="image"' % embed_pk
                        old_embed_attrs = 'data-id="%s"' % fig_id

                        story.body.content = story.body.content.replace(old_embed_attrs, new_embed_attrs)
                    story.save()
                    story.invalidate()

            except Exception as e:
                print(e)
                continue
