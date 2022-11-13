import json, time, datetime, operator
from django.db.models import Q
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, DeleteView, FormView
from django.views.generic.base import View
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import patch_cache_control, never_cache
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.conf import settings
from lib.views import GenericFollowView, GenericUnFollowView

from lib.utils import api_serialize_resource_obj, get_serialized_list, suite_render
from articles.utils import render_teasers
from django.contrib.auth import get_user_model
from articles.models import Article
from suites.models import Suite
from lib.cache import get_object_from_pk, get_object_from_hash
from lib.mixins import AjaxableResponseMixin, CachedObjectMixin
from lib.enums import *
from profiles.api import UserMiniResource
from .sets import *
from .forms import PostUploadImageForm
from .api import ConversationResource, PostResource
from .models import Conversation, Post
     
class ConversationDetailView(DetailView, CachedObjectMixin, AjaxableResponseMixin):
    model = Conversation
    hashed_id = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.hashed_id = kwargs.get('hashed_id')
        response = super(ConversationDetailView, self).dispatch(*args, **kwargs)
        return response

    def get_object(self, queryset=None):
        return get_object_from_hash(self.hashed_id)

    def get(self, request, *args, **kwargs):
        from notifications.tasks import clear_unread_notifications
        has_page_param = self.request.GET.get('page', None)
        page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.is_ajax = True if self.request.is_ajax() and not self.spa_fetch else False

        self.has_next = False
        self.has_prev = False

        start = (page_num - 1) * DEFAULT_PAGE_SIZE
        end = page_num * DEFAULT_PAGE_SIZE + 1        
        
        self.object = self.get_object()
        self.feed = None

        if self.is_ajax:
            return self.render_to_json_response({
                "objects": self.feed
            })

        clear_unread_notifications(request.user, content_object=self.object)    

        if self.spa_fetch:
            innercontext = self.get_inner_context()
            return self.render_to_json_response(innercontext)

        return super(ConversationDetailView, self).get(request, args, kwargs)

    def get_inner_context(self):
        if not self.spa_fetch:
            innercontext = api_serialize_resource_obj(self.object, ConversationResource(), self.request)
        else:
            innercontext = {}

        innercontext['isMod'] = self.request.user.is_moderator
        innercontext['currentUser'] = api_serialize_resource_obj(self.request.user, UserMiniResource(), self.request)
        innercontext['userLoggedIn'] = self.request.user.is_authenticated()

        if self.request.user.is_authenticated():
            if self.request.user == self.object.owner or self.request.user.is_moderator:
                innercontext['ownerViewing'] = True

        posts, more_posts = self.object.get_posts(self.request, None)
        innercontext['posts'] = posts
        innercontext['more_posts'] = more_posts
   
        return innercontext

    def get_context_data(self, **kwargs):
        context = super(ConversationDetailView, self).get_context_data(**kwargs)
        innercontext = self.get_inner_context()               
        context['conv_json'] = json.dumps(innercontext)
        context['conv_detail_rendered'] = suite_render(self.request, 'conversation-detail', innercontext)
        return context

class ConversationCreateView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ConversationCreateView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        ''' build the new chat object and return and id for pageController '''
        User = get_user_model()
        first_message = request.POST.get('message', '')
        chat_owner = request.user
        member_string = request.POST.get('members', '')
        chat_members = json.loads(member_string)

        chat = Chat.objects.create(owner=chat_owner)

        if not chat:
            raise Http404

        # should always have at least the one
        if chat_members: 
            for mem in chat_members:
                try:
                    user = User.objects.get(pk=mem['id'])
                    member, created = ChatMember.objects.get_or_create(chat=chat, user=user)
                except Exception as e:
                    print(e)
                    pass

        if first_message:
            try:
                ChatMessage.objects.create(chat=chat, user=request.user, message=first_message)
            except Exception as e:
                pass

        return HttpResponse(chat.get_absolute_url())


class PostImageUploadView(AjaxableResponseMixin, FormView):
    form_class = PostUploadImageForm
    template_name = 'conversations/upload.html'  # doesn't get used.
    success_url = '/asdfsdafdsafdasf'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PostImageUploadView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):   
        from PIL import Image
        from lib.tasks import resize_image
        self.story = None

        image = form.save(commit=False)
        story_id = self.request.POST.get('storyid', None)
        is_cover = True if self.request.POST.get('cover', '') == 'true' else False
        if story_id:
            try:
                self.story = Article.objects.get(pk=story_id)
            except:
                pass

        # 16MB
        MAX_SIZE = 10*1024*1024 

        # def pil_to_django(image, format="JPEG"):
        #     # http://stackoverflow.com/questions/3723220/how-do-you-convert-a-pil-image-to-a-django-file
        #     fobject = StringIO.StringIO()
        #     image.save(fobject, format=format)
        #     return ContentFile(fobject.getvalue())

        def returnError(error):
            # do we need to return different error types?
            return self.render_to_json_response({
                "error": error
            }) 

        def valid_image_size(image, max_size=MAX_SIZE):
            width, height = image.size
            if (width * height) > max_size:
                return False
            return True

        def get_mimetype(img_object):
            mime = magic.Magic(mime=True)
            mimetype = mime.from_buffer(img_object.read(1024))
            img_object.seek(0)
            return mimetype

        def valid_image_mimetype(img_object):
            # http://stackoverflow.com/q/20272579/396300
            mimetype = get_mimetype(img_object)
            if mimetype:
                return mimetype.startswith('image')
            else:
                return False 

        import magic
        VALID_IMAGE_MIMETYPES = [
            "image"
        ]

        if not valid_image_mimetype(image.image):
            return _invalidate(_("Downloaded file was not a valid image"))

        pil_image = Image.open(image.image)
        if not valid_image_size(pil_image):
            error = "That image is too large to upload"
            return self.render_to_json_response({
                "error": error
            }) 

        # django_img = pil_to_django(pil_image)
        image.save()
        resize_story_image(image)

        embed_object, created = StoryEmbed.objects.get_or_create(story=self.story, object_id=image.pk, content_type=ContentType.objects.get_for_model(ArticleImage))
        if not embed_object:
            return _invalidate(_("Oh! Something went wrong creating the embed. Please try again."))
        if is_cover:
            embed_object.cover = True
            embed_object.save()

        embed_json = api_serialize_resource_obj(embed_object, StoryEmbedResource(), self.request)
        
        return self.render_to_json_response({
            'media': embed_json,
            'type': 'image'
            })


class PostMediaEmbedView(AjaxableResponseMixin, View):   
    ''' General post embed functions; users can embed Link, Image or Post model objects '''
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(PostMediaEmbedView, self).dispatch(request, *args, **kwargs)

    def returnError(self):
        # do we need to return different error types?
        return self.render_to_json_response({
            "error": True
        })  

    def post(self, request, *args, **kwargs):
        from links.models import Link
        from suites.models import Suite
        from links.utils import get_object_from_input
        from lib.models import GenericImage

        self.story = None
        embed_string = request.POST.get("embedstring", "")

        is_photo = ['photo','image']
        json_object = None

        post_id = self.request.POST.get('storyid', None)
        is_cover = True if self.request.POST.get('cover', '') == 'true' else False
        if post_id:
            try:
                self.post = Post.objects.get(pk=post_id)
            except:
                pass

        embed_object = get_object_from_input(request, embed_string)
        
        if not embed_object:
            self.returnError()
         
        if embed_object:
            if isinstance(embed_object, Post):
                embed_type = 'post'
            elif isinstance(embed_object, Suite):
                embed_type = 'suite'
            elif isinstance(embed_object, Link):
                if embed_object.media_type in is_photo:
                    raw_string = json.loads(embed_object.oembed_string)                    
                    try:
                        img_auth_name = raw_string['authors'][0]['name']
                    except:
                        img_auth_name = ''
                    try:
                        img_auth_url = raw_string['authors'][0]['url']
                    except:
                        img_auth_url = ''
                    try:
                        img_title = raw_string['title']
                    except:
                        img_title = ''
                    response = {}
                    try:
                        image_url = embed_object.get_media_url()
                        image = GenericImage.objects.create(upload_url=image_url)
                        more_to_add = False
                        if img_title:
                            image.caption = img_title
                            more_to_add = True
                        if img_auth_name:
                            image.credit = img_auth_name
                            more_to_add = True
                        if img_auth_url:
                            image.credit_link = img_auth_url
                            more_to_add
                        if more_to_add:
                            image.save()

                        if not image:
                            return self.render_to_json_response({
                                "error": True,
                                "msg": "Ack! Something went wrong uploading that image. Please try again."
                            })                             

                        resize_story_image(image)
                        embed_type = 'image'
                        embed_object = image

                    except Exception as e:
                        return self.render_to_json_response({
                            "error": True,
                            "msg": "No! Something went wrong uploading that image. Please try again."
                        })

                else:
                    embed_type = 'link'

        if not embed_object:
            self.returnError()

        embed = StoryEmbed.objects.create(story=self.story, content_type=ContentType.objects.get_for_model(embed_object), object_id=embed_object.pk)
        if is_cover:
            embed.cover = True
            embed.save()

        embed_json = api_serialize_resource_obj(embed, StoryEmbedResource(), self.request)

        return self.render_to_json_response({
            'media': embed_json,
            'type': embed_type
            })

def article_image_owner(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request or not request.user:
            return HttpResponseRedirect(reverse('login'))

        pk = kwargs.get('pk', None)
        article_image = get_object_from_pk(ArticleImage, pk=pk)

        if article_image.article and not article_image.article.author == request.user and not request.user.is_moderator:
            return HttpResponseRedirect('/')

        return view_func(request, *args, **kwargs)
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)

class HashtagAutocompleteView(AjaxableResponseMixin, View):

    def get(self, request, *args, **kwargs):
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection(slave=True)

        partial_tag = str(request.GET.get('q', ''))
        query_range_min = "[%s" % partial_tag
        query_range_max = "[%s\xff" % partial_tag
        key = 'tags'

        matching_tags = redis.zrangebylex(key, query_range_min, query_range_max)
        data = [tag for tag in matching_tags]

        return HttpResponse(json.dumps(data), mimetype='application/json')

class FetchSerializedPost(AjaxableResponseMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        self.pk = kwargs.get('pk', None)
        return super(FetchSerializedPost, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            post = get_object_from_pk(Post, self.pk, False) 
        except Exception as e:
            raise Http404

        def authed():
            if post.published and post.author.is_active:
                return True
            if post.deleted:
                raise Http404
            if not request.user.is_authenticated():
                raise Http404
            # This leaves drafts and published stories from inactive users - let author and mods see these
            return post.author == bundle.request.user or bundle.request.user.is_moderator

        try:
            if not authed():
                raise Http404
        except Exception as e:
            print(e)

        return self.render_to_json_response(api_serialize_resource_obj(story, PostResource(), request))

class FetchConvParentView(AjaxableResponseMixin, View):
    @method_decorator(login_required)
    @method_decorator(never_cache)    
    def dispatch(self, *args, **kwargs):
        return super(FetchConvParentView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        ''' first try to fetch stories or links; 
            if no results, try to match either the hash or (for Link objects) the link;
            if no results, try to fetch oembed string and build a Link object '''
        from links.models import Link        
        from articles.api import StoryMiniResource
        from links.api import LinkMiniResource
        from links.utils import get_object_from_input
        self.page_num = int(self.request.GET.get('page', '1'))
        self.spa_fetch = True if request.GET.get('spa', '') == 'true' else False
        self.query = str(self.request.GET.get('q', ''))
        if self.query.find('?') > 0:
            self.query = self.query[:self.query.find('?')] # remove querystrings

        self.named_filter = str(self.request.GET.get('filter', ''))

        self.start = (self.page_num - 1) * DEFAULT_PAGE_SIZE  
        self.end = self.page_num * DEFAULT_PAGE_SIZE + 1
        self.has_previous = True if self.page_num > 1 else False
        self.has_next = False
        pks = None
        results = []

        if self.query:
            from haystack.query import SearchQuerySet
            try:
                raw_results = SearchQuerySet().models(Link, Article).auto_query(self.query)[self.start:self.end]
            except Exception as e:
                pass            
            results = []
            try:
                if raw_results:
                    for thing in reversed(raw_results):
                        thing_object = None
                        if thing.model_name == 'link':
                            # TODO: adapt get_serialized_list to multi-model requests
                            thing_object = get_serialized_list(request, [thing.pk],'link:mini')
                        elif thing.model_name == 'article':
                            thing_object = get_serialized_list(request, [thing.pk],'story:mini')
                        if not thing_object:
                            continue
                        results.append(thing_object[0])
            except:
                pass

            if not results:
                external_fetch = get_object_from_input(request, self.query)
                if external_fetch:
                    if ContentType.objects.get_for_model(external_fetch) == ContentType.objects.get_for_model(Link):
                        results.append(api_serialize_resource_obj(external_fetch, LinkMiniResource(), request))
                    elif ContentType.objects.get_for_model(external_fetch) == ContentType.objects.get_for_model(Article):
                        results.append(api_serialize_resource_obj(external_fetch, StoryMiniResource(), request))

            return self.render_to_json_response({
                    "objects": results
                }) 

        else:
            return HttpResponse(None)

    def post(self, request, *args, **kwargs):
        from lib.sets import RedisObject
        from lib.utils import get_client_ip
        from django.db.models import Q
        from links.models import Link
        from links.api import LinkMiniResource, LinkResource
        from links.utils import get_object_from_input

        query_string = request.POST.get('q', '')
        parent_object = get_object_from_input(request, query_string)
        json_object = None

        if not parent_object:
            return self.render_to_json_response({
                "error": True
            }) 
 
        if isinstance(parent_object, Article):
            resource = StoryMiniResource()
        elif isinstance(parent_object, Link):
            resource = LinkMiniResource()

        try:
            json_object = api_serialize_resource_obj(parent_object, resource, request)
        except Exception as e:
            print(e)

        if not json_object:
            return self.render_to_json_response({
                "error": True
            }) 

        else:
            return self.render_to_json_response({
                "obj": json_object
            })  
