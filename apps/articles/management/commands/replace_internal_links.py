import csv

from django.core.management.base import BaseCommand
from BeautifulSoup import BeautifulSoup as soup

from articles.models import Article


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        filename = args[0]

        with open(filename, 'rU') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            import pdb; pdb.set_trace()

            for row in reader:
                try:
                    article_slug = row[0]
                    original_link = ','.join(row[3:])
                    replacement_link = row[2]
                except:
                    continue

                article_slug = article_slug.split('/')[-1]
                try:
                    article = Article.objects.get(slug=article_slug)
                except:
                    print row
                    # print "Can't find article %s" % article_slug
                    continue

                # ok we have an article, now let's replace the link.
                if 'https://suite101.com' in replacement_link:
                    import pdb; pdb.set_trace()
                    try:
                        html = soup(replacement_link)
                        tags = [tag for tag in html.findAll('a')]
                        tag = tags[0]
                        href = tag.get('href')
                    except:
                        print row
                        #print "Error pulling out internal href %s" % replacement_link
                        pass
                    else:
                        # this is an internal link, we have to check to see if we need to replace it
                        internal_slug = href.split('/')[-1]
                        try:
                            linked_article = Article.objects.get(slug=internal_slug)
                        except:
                            pass
                        else:
                            new_internal_url = '/%s/%s' % (linked_article.author.slug, linked_article.get_hashed_id())
                            replacement_link = replacement_link.replace(href, new_internal_url)

                original_link = original_link.strip()
                if not original_link in article.body.content:
                    print row
                    continue

                article.body.content = article.body.content.replace(original_link, replacement_link)
                article.save()
                article.invalidate()





