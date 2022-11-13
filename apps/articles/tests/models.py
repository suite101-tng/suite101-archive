from lib.tests import Suite101BaseTestCase
from django.contrib.contenttypes.models import ContentType
from articles.models import Article, ArticleImage


class TestArticleModels(Suite101BaseTestCase):
    def setUp(self):
        super(TestArticleModels, self).setUp()
        self.article = Article.objects.create(
            title='test article',
            author=self.user
        )

    def tearDown(self):
        del self.article

    def test_unicode(self):
        self.assertEqual(self.article.__unicode__(), 'test article (%s)' % self.article.pk)

    def test_absolute_url(self):
        self.assertEqual(self.article.get_absolute_url(), '/test-user/%s' % self.article.get_hashed_id())

    def test_autoslug_long(self):
        self.article2 = Article()
        self.article2.author = self.user
        self.article2.title = 'This is a very long title sldjfalskjdflaksjfdlkajsfldkjaslkfdjaslkfjalksfjdlkasjflkasjflkajslfdkjalskfjaslkfjlaskjflkasjflkajslfkjalaksjdflkajsdlfkjaslkfjalksjdflaksjfdlksadjflkajslkfjaslkfjsdf'
        self.article2.save()
        self.assertEqual(self.article2.slug, 'this-is-a-very-long-title-sldjfalskjdflaksjfdlkajsfldkjaslkfdjaslkfjalksfjdlkasjflkasjflkajslfdkjals')

    def test_autoslug_no_title(self):
        self.article2 = Article()
        self.article2.author = self.user
        self.article2.title = ''
        self.article2.save()
        self.assertEqual(self.article2.slug, 'untitled')        

    def test_draft_property(self):
        self.assertTrue(self.article.draft)

    def test_published_property(self):
        self.article.status = Article.STATUS.published
        self.article.save()
        self.assertTrue(self.article.published)

    def _setup_suite(self):
        from suites.models import Suite, SuitePost
        self.suite = Suite.objects.create(owner=self.user, name='test suite')
        self.article.status = Article.STATUS.published
        self.article.save()
        self.article2 = Article.objects.create(title='next story', author=self.user, status=Article.STATUS.published)
        self.suitestory1 = SuitePost.objects.create(content_type=ContentType.objects.get_for_model(self.article), object_id=self.article.pk, suite=self.suite)
        self.suitestory2 = SuitePost.objects.create(content_type=ContentType.objects.get_for_model(self.article2), object_id=self.article2.pk, suite=self.suite)

    def test_mark_deleted(self):
        self.article.mark_deleted()
        self.assertEqual(self.article.status, Article.STATUS.deleted)

    def test_article_manager_published(self):
        self.assertEqual(Article.objects.published().count(), 0)

    def test_article_manager_archived(self):
        self.assertEqual(Article.objects.archived().count(), 0)

    def test_article_manager_draft(self):
        self.assertEqual(Article.objects.drafts().count(), 1)
