from __future__ import unicode_literals
from django.core.management.base import BaseCommand
from django.utils.encoding import smart_str, smart_text
import datetime, time
from bs4 import BeautifulSoup as soup
import HTMLParser
import re
from django.contrib.contenttypes.models import ContentType
from articles.models import Article, ArticleImage, StoryEmbed
from lib.models import GenericImage
from conversations.models import *
from lib.enums import *

class Command(BaseCommand):
    help = 'usage: python manage.py migrate_articles_to_conversations'

    def handle(self, *args, **options):   
        epoch = datetime.datetime.strptime(SUITE_EPOCH, "%Y-%m-%d")
        # articles = Article.objects.published().filter(author__approved=True, author__is_active=True, created__gte=epoch)
        articles = Article.objects.published().filter(pk=204837)

        for article in articles.iterator():
            owner = article.author
            # conversation = Conversation.objects.create(owner=article.author)
            # if article.subtitle:
            #     conversation.description = article.description
            #     conversation.save()

            # open up article body and try to find old embeds
            try:
                # clean up the body
                body = article.body.content.encode('utf-8')
                body = body.decode('utf-8').replace('\u2013','-')
                body = body.decode('utf-8').replace('\u2014','-')
                body = body.decode('utf-8').replace('\u2015','-')
                body = body.decode('utf-8').replace('\u2019','-')
                article.body.content = body
                article.save()

                html = soup(article.body.content, "html.parser")
                figures = html.findAll('figure')
                figs = [fig for fig in figures]
                if figs:
                    for fig in figs:
                        new = str(fig) + 'PPPPPPPPPPP'
                        new = soup(new, 'html.parser')
                        fig.replaceWith(new)
                    article.body.content = html.encode('utf-8')
                    print(article.body.content)
                    # article.save()

                    # print(unicode(str(body), 'utf-8'))
                    # print(article.body.content)
                    # article.save()
                    # print(html)
                    # article.body.content = body
                    # print(body)
                    # article.body.content = html.encode('utf8')
                    # article.save()


                        # try:
                        #     fig_id = re.findall(r'data-id="([^"]*)"', str(fig))[0]  
                        #     article_image = ArticleImage.objects.get(pk=fig_id)
                        #     print 'create a new GenericImage with the file at %s' % article_image.get_orig_image_url()
                        #     img_url = article_image.get_orig_image_url()
                        #     caption = article_image.caption or ''
                        #     credit = article_image.credit or ''
                        #     credit_link = article_image.credit_link or ''
                        #     generic_image = GenericImage.objects.create(user=article.author, upload_url=img_url)
                        #     generic_image.credit = credit
                        #     generic_image.credit_link = credit_link
                        #     generic_image.caption = caption
                        #     generic_image.save()

                        #     # print 'we have a figure with ID %s' % fig_id
                        # except: 
                        #     pass

                        # embed_part_one = '<figure contenteditable="false" unselectable="on" class="inlineImageWrapper" data-id="%s" itemscope itemtype="http://schema.org/ImageObject"><img src="%s" alt="%s" data-id="%s" data-caption="%s" data-credit="%s" data-credit-link="%s" data-type="image" data-width="%s" data-height="%s" itemprop="contentUrl"/><figcaption class="imageCaption" data-id="%s"><div class="story-embed-caption storyEmbedCaption" itemprop="caption"><span class="main-cap">%s</span>' % (embed_id, img_url, embed_id, caption, credit, credit_link, width, heigh, embed_id, caption)
                        # embed_part_two = '<span class="credit"><a class="wrapping-anchor" href="%s" target="_blank">%s</a></span>' % (credit_link, credit) if credit_link else ''
                        # embed_part_three = '</div></figcaption></figure>'

                        # new_embed = embed_part_one + embed_part_two + embed_part_three


            except Exception as e:
                print('failed to parse article body for figures: %s' % e)


        # image_string = 'data-type="image"'
        # for story in stories.iterator():
        #     try:
        #         html = soup(story.body.content, "html5lib")
        #         figures = html.findAll('figure')
        #         figs = [fig for fig in figures]
        #         if figs:
        #             # data-id="188449"
        #             for fig in figs:
        #                 try:
        #                     fig_id = re.findall(r'data-id="([^"]*)"', str(fig))[0]
        #                     # if fig_id:
        #                     #     print 'we have a fig id: %s' % fig_id
        #                     #     fig_id = fig_id[0]
        #                     #     try:
        #                     #         image = ArticleImage.objects.get(pk=fig_id)
        #                     #     except:
        #                     #         image = None
        #                     #     if image:
        #                     #         story_embed = StoryEmbed.objects.create(story=story, object_id=fig_id, content_type=ContentType.objects.get_for_model(ArticleImage))       
        #                     #         embed_pk = story_embed.pk                     
        #                     #         print 'we have a new story_embed object: %s' % embed_pk
        #                     #     else:
        #                     #         embed_pk = fig_id
        #                 except Exception as e:
        #                     print 'nope: %s' % e
        #                     # continue

        #                 new_embed_attrs = 'data-id="%s" data-type="image"' % embed_pk
        #                 old_embed_attrs = 'data-id="%s"' % fig_id

        #                 print 'about to replace %s with %s' % (old_embed_attrs, new_embed_attrs)
        #                 story.body.content = story.body.content.replace(old_embed_attrs, new_embed_attrs)
        #             story.save()
        #             story.invalidate()

        #     except Exception as e:
        #         print(e)
        #         continue
