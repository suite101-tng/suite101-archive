import datetime, time, json, re, operator
from articles.templatetags import upto
from suites.models import Suite, SuitePost
from django.template.defaultfilters import truncatechars, date, wordcount, escape, timesince
from django.utils.html import strip_tags
from django.conf.urls import url
from django.http import HttpRequest, Http404
from django.contrib.contenttypes.models import ContentType

from tastypie.resources import Resource
from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.validation import FormValidation, Validation
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.bundle import Bundle
from haystack.query import SearchQuerySet
from lib.utils import api_serialize_resource_obj
from lib.cache import get_object_from_pk
from lib.utils import percentage
from profiles.api import UserMiniResource
from django.contrib.auth import get_user_model
from lib.utils import get_serialized_list

from lib.models import Follow

from lib.api import Suite101Resource, Suite101BaseAuthorization, Suite101ModelFormValidation, Suite101SearchResource
from suites.api import SuiteMiniResource

from links.api import LinkMiniResource
from links.models import Link
from .models import Article, ArticleImage, StoryParent, StoryEmbed
from .forms import ArticleCreateForm, ArticleImageAttrsUpdateForm

from articles.templatetags.ptag import ptag
from articles.templatetags.nofollow import nofollow
from articles.templatetags.abs_to_rel import abs_to_rel
from articles.templatetags.bleach_filter import bleach_filter
from articles.utils import _post_article_publish


class StoryAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        # for now allow all users to view any list of published stories
        return object_list.filter(status=Article.STATUS.published)

    def read_detail(self, object_list, bundle):
        """ anyone can see published stories by active members """
        if bundle.obj.published and bundle.obj.author.is_active:
            return True
        if bundle.obj.deleted:
            raise Http404
        if not bundle.request.user.is_authenticated():
            raise Http404
        # This leaves drafts and published stories from inactive users - let author and mods see these
        return bundle.obj.author == bundle.request.user or bundle.request.user.is_moderator

    def update_detail(self, object_list, bundle):
        if not bundle.request.user.is_authenticated():
            return False
        return bundle.obj.author == bundle.request.user or bundle.request.user.is_moderator

    def delete_detail(self, object_list, bundle):
        if not bundle.request.user.is_authenticated():
            return False
        return bundle.obj.author == bundle.request.user or bundle.request.user.is_moderator

class StoryMiniResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'story_mini'
        data_cache_key = 'story:mini'    
        queryset = Article.objects.published().select_related('author')
        include_absolute_url = True
        authorization = ReadOnlyAuthorization()            

        fields = [
            'id',
            'title',
            'slug',
            'status',
        ]

        filtering = {
            'status': 'exact',
            'author': ALL_WITH_RELATIONS
        }

    def dehydrate(self, bundle):
        story = bundle.obj
        bundle.data['story_resource_uri'] = StoryResource().get_resource_uri(story)
        bundle.data['title'] = story.title if story.title and not story.title == 'Untitled' else None
        bundle.data['hash'] = story.hashed_id
        bundle.data['obj_type'] = 'story'
        bundle.data['ctype'] = ContentType.objects.get_for_model(story)
        bundle.data['story_type'] = True
        bundle.data['auth_active'] = story.author.is_active

        try:
            bundle.data['created'] = time.mktime(story.created.timetuple())
            bundle.data['created_formatted'] = story.created.strftime('%a %b %d %H:%M:%S +0000 %Y')
        except:
            pass
        try:
            bundle.data['updated'] = time.mktime(story.modified.timetuple())
        except:
            pass
        bundle.data['author'] = api_serialize_resource_obj(story.author, UserMiniResource(), bundle.request)

        bundle.data['draft'] = True if story.status == 'draft' else False        
        bundle.data['heading'] = story.get_heading()

        try:
            bundle.data['excerpt'] = strip_tags(truncatechars(bleach_filter(story.body.excerpt, ['p']), 120))
        except:
            bundle.data['excerpt'] = 'Empty draft'

        return bundle

    def get_object_list(self, request):
        return super(StoryMiniResource, self).get_object_list(request)


class StoryResource(Suite101Resource):
    author = fields.ToOneField('profiles.api.UserMiniResource', 'author')

    class Meta(Suite101Resource.Meta):
        data_cache_key = 'story:full'
        cache_authed = False
        resource_name = 'story'
        queryset = Article.objects.all().select_related('author')
        authorization = StoryAuthorization()
        validation = Suite101ModelFormValidation(form_class=ArticleCreateForm)
        always_return_data = True

        fields = [
            'id',
            'body',
            'status',
            'title',
            'embeds',
            'subtitle',
            'subtitle_class',
            'saved_on',
            'archive',
            'slug',
            'featured',
            'tag_list',
            'deferred',
            'story_parent',
            'words_changed',
            'story_parent'
        ]

        filtering = {
            'author': 'exact',
        }

    """ dehydrate cycle - serializing the object to json """
    def dehydrate(self, bundle):
        story = bundle.obj
        recommended_pks = []

        bundle.data['mini_resource_uri'] = StoryMiniResource().get_resource_uri(story)
        bundle.data['author'] = api_serialize_resource_obj(story.author, UserMiniResource(), bundle.request)

        # Core story stats  
        bundle.data['stats'] = json.loads(story.get_story_stats())

        if story.created:
            bundle.data['created'] = json.dumps(time.mktime(story.created.timetuple()))
        if story.modified:
            bundle.data['modified'] = json.dumps(time.mktime(story.modified.timetuple()))

        year = datetime.datetime.now() - datetime.timedelta(days=365)
        if story.created < year:
            bundle.data['year_old'] = True
            bundle.data['created_short'] = date(bundle.obj.created, "M j, Y")

        bundle.data['title'] = story.title.replace('\n', ' ')
        bundle.data['subtitle'] = story.subtitle.strip()
        bundle.data['hash'] = story.hashed_id
        bundle.data['title_escaped'] = escape(story.title.replace('\n', ' '))
        bundle.data['is_published'] = story.published
        bundle.data['is_draft'] = story.status == Article.STATUS.draft
        bundle.data['is_deleted'] = story.status == Article.STATUS.deleted
        bundle.data['word_count'] = story.word_count if story.word_count else story.get_word_count(update=False)
        bundle.data['body'] = bleach_filter(abs_to_rel(nofollow(ptag(story.body.content, story),story.author)))
        bundle.data['body_excerpt'] = truncatechars(bleach_filter(story.body.excerpt, ['p']), 200)
        bundle.data['body_excerpt_no_tags'] = strip_tags(truncatechars(bleach_filter(story.body.excerpt, ['p']), 280))

        tags = []
        if story.tag_list:
            try:
                tags = json.loads(story.tag_list)
                if tags:
                    tags_obj = [{'tag': '%s' % tag, 'tagUrl': '/q/%s' % (re.sub('[^0-9a-zA-Z]+', '-', tag).lower())} for tag in tags]
                    bundle.data['tag_list'] = tags_obj
            except Exception as e:
                pass

        if hasattr(bundle.request, 'user') and bundle.request.user.is_authenticated():
            bundle.data['ownerViewing'] = bundle.request.user == story.author or bundle.request.user.is_moderator
            if bundle.request.user.is_moderator:
                bundle.data['isMod'] = True
                bundle.data['approved'] = True if story.author.approved else False 

            if 'author' in bundle.data:
                if bundle.request.user == story.author or bundle.request.user.is_moderator:
                    bundle.data['is_author'] = True          

        if wordcount(story.body.content) < 400:
            bundle.data['short'] = True

        return bundle

    """ hydrate cycle - json to model """
    def hydrate(self, bundle):
        if not 'title' in bundle.data:
            bundle.data['title'] = 'Untitled'
        if 'author' in bundle.data:
            del bundle.data['author']
        if 'num_followers' in bundle.data:
            del bundle.data['num_followers']
        if 'images' in bundle.data:
            del bundle.data['images']

        return bundle

class StoryParentResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'story_parent'
        data_cache_key = 'story:parent'    
        queryset = StoryParent.objects.all()
        list_allowed_methods = ['post', 'get']
        include_absolute_url = False
        authorization = ReadOnlyAuthorization()            

        fields = [
            'id'
        ]

        filtering = {
            'story': ALL_WITH_RELATIONS
        }

    def dehydrate(self, bundle):
        story_parent = bundle.obj
        resource = None

        if story_parent.content_type == ContentType.objects.get_for_model(Article):
            resource = StoryMiniResource()
        elif story_parent.content_type == ContentType.objects.get_for_model(Link):
            resource = LinkMiniResource()

        if not resource:
            return None
        bundle.data = api_serialize_resource_obj(story_parent.content_object, resource, bundle.request)
        return bundle

    def get_object_list(self, request):
        return super(StoryParentResource, self).get_object_list(request)

class StoryEmbedResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'story_embed'
        data_cache_key = None    
        queryset = StoryEmbed.objects.all()
        include_absolute_url = False
        authorization = ReadOnlyAuthorization()            

        fields = [
        ]

        filtering = {
            'object_id': 'exact',
            'content_type': 'exact',
        }

    def dehydrate(self, bundle):
        embed = bundle.obj

        if embed.content_type == ContentType.objects.get_for_model(ArticleImage):
            bundle.data['image_type'] = True
            bundle.data['spill'] = embed.spill
            bundle.data['caption'] = embed.caption.strip()
            try:
                bundle.data['embed_object'] = api_serialize_resource_obj(embed.content_object, StoryImageResource(), bundle.request)
                bundle.data['embed_object']['show_caption'] = True if embed.content_object.caption or embed.content_object.credit or embed.content_object.credit_link else False
                bundle.data['embed_object']['orig_image_url'] = embed.content_object.get_orig_image_url()
                bundle.data['embed_object']['large_image_url'] = embed.content_object.get_large_image_url()
                bundle.data['embed_object']['small_image_url'] = embed.content_object.get_small_image_url()
                try:
                    bundle.data['width'] = bundle.obj.image.width
                    bundle.data['height'] = bundle.obj.image.height
                except:
                    pass            
            except Exception as e:
                print('failed to serialize image in storyembedresource(): %s' % e)
        
        elif embed.content_type == ContentType.objects.get_for_model(Link):
            bundle.data['link_type'] = True
            bundle.data['embed_object'] = api_serialize_resource_obj(embed.content_object, LinkMiniResource(), bundle.request)

        elif embed.content_type == ContentType.objects.get_for_model(Article):
            bundle.data['story_type'] = True
            bundle.data['embed_object'] = api_serialize_resource_obj(embed.content_object, StoryMiniResource(), bundle.request)

        return bundle

    def get_object_list(self, request):
        return super(StoryEmbedResource, self).get_object_list(request)

class StoryImageAuthorization(Suite101BaseAuthorization):
    def update_detail(self, object_list, bundle):
        # hole here.. article images for a short time don't have an owner...
        if bundle.obj.article:
            return bundle.obj.article.author == bundle.request.user or bundle.request.user.is_moderator
        return True

    def delete_detail(self, object_list, bundle):
        if bundle.obj.article:
            return bundle.obj.article.author == bundle.request.user or bundle.request.user.is_moderator
        return True

class StoryImageResource(Suite101Resource):
    story = fields.ToOneField(StoryResource, 'article', null=True)

    class Meta(Suite101Resource.Meta):
        resource_name = 'story_image'
        data_cache_key = 'story:img'
        cache_lifespan = 86400
        queryset = ArticleImage.objects.all().using('default')
        include_absolute_url = False
        authorization = StoryImageAuthorization()
        validation = FormValidation(form_class=ArticleImageAttrsUpdateForm)
        list_allowed_methods = []  # no real need for a list
        detail_allowed_methods = ['get', 'put', 'delete']
        always_return_data = True

        fields = [
            'id',
            'is_main_image',
            'credit',
            'credit_link',
            'image_type',
        ]

    def dehydrate(self, bundle):
        if bundle.obj.image:
            bundle.data['show_caption'] = True if bundle.obj.caption or bundle.obj.credit or bundle.obj.credit_link else False
            bundle.data['orig_image_url'] = bundle.obj.get_orig_image_url()
            bundle.data['large_image_url'] = bundle.obj.get_large_image_url()
            bundle.data['small_image_url'] = bundle.obj.get_small_image_url()
            try:
                bundle.data['width'] = bundle.obj.image.width
                bundle.data['height'] = bundle.obj.image.height
            except:
                pass
        return bundle

    def hydrate(self, bundle):
        if 'orig_image_url' in bundle.data:
            del bundle.data['orig_image_url']
        if 'large_image_url' in bundle.data:
            del bundle.data['large_image_url']
        if 'small_image_url' in bundle.data:
            del bundle.data['small_image_url']
        if 'width' in bundle.data:
            del bundle.data['width']
        if 'height' in bundle.data:
            del bundle.data['height']

        bundle = self.extract_resource_uri(bundle, 'story')
        return bundle


    """ RESTFUL object methods """
    def obj_update(self, bundle, **kwargs):
        response = super(StoryImageResource, self).obj_update(bundle, **kwargs)

        bundle.obj.invalidate()
        if 'is_main_image' in bundle.data and bundle.data['is_main_image']:
            new_image_pk = bundle.data['pk']
            try:
                bundle.obj.article.images.filter(is_main_image=True).exclude(pk=new_image_pk).delete()
            except:
                pass
        return response

class StorySearchResource(Suite101SearchResource):
    class Meta:
        model = Article
        queryset = Article.objects.all()
        resource_name = 'stories'
        url_name = 'api_story_search'
    
    def do_search(self, request, *args, **kwargs):
        from links.models import Link
        from haystack.query import SQ
        raw_results = None
        start = kwargs.get('start', 0)
        end = kwargs.get('end', 15)
        query = kwargs.get('query', '')
        mlt = kwargs.get('mlt',False)
        exclude = kwargs.get('exclude',[])
        results = []

        if query: 
            query = [q for q in query.split(' ') if not q==""]
            sq = reduce(operator.__or__, [SQ(content=q) for q in query])
            raw_results = SearchQuerySet().models(Link, Article).filter(sq)[start:end]

            if raw_results:
                for thing in reversed(raw_results):
                    thing_object = None
                    if thing.model_name == 'link':
                        # TODO: adapt get_serialized_list to multi-model requests
                        thing_object = get_serialized_list(request, [int(thing.pk)],'link:mini')
                    elif thing.model_name == 'article':
                        thing_object = get_serialized_list(request, [int(thing.pk)],'story:mini')
                    else:
                        continue
                    if thing_object:
                        results.append(thing_object[0])

        # else:
        #     raw_results = self.get_default_queryset()

        return results

    def get_serialized_objs(self, request, obj_list): 
        try:
            for obj in obj_list:
                objects = get_serialized_list(request, obj_list, 'story:mini')
        except Exception as e:
            return []
        return objects

    def serialize_obj(self, obj):
        return api_serialize_resource_obj(obj, StoryMiniResource(), HttpRequest())

class UserStorySearchResource(StorySearchResource):
    class Meta:
        model = Article
        queryset = Article.objects.all()
        resource_name = 'user_stories'
        url_name = 'api_user_story_search'

    def _fetch_search_results(self, query, request):
        from haystack.query import SearchQuerySet
        if query:
            try:
                user = request.user
                return SearchQuerySet().models(self._meta.model).filter(author=user.get_full_name()).auto_query(query)
            except:
                return super(UserStorySearchResource, self)._fetch_search_results(query, request)
        else:
            return self.get_default_queryset(request)

    def get_default_queryset(self, request):
        try:
            user = request.user
            return self._meta.model.objects.all().filter(author=user)
        except:
            return super(UserStorySearchResource, self).get_default_queryset()

    def serialize_obj(self, obj):
        return api_serialize_resource_obj(obj, StoryMiniResource(), HttpRequest())
