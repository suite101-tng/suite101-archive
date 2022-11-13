import time, datetime
from conversations.templatetags import upto
from django.template.defaultfilters import truncatechars, date, timesince, safe
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

from django.http import HttpResponse, Http404, HttpRequest
from tastypie import fields
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.contrib.contenttypes.fields import GenericForeignKeyField
from tastypie.exceptions import NotFound, Unauthorized
from tastypie.validation import Validation
from tastypie.resources import Resource

from lib.api import Suite101Resource, Suite101BaseAuthorization
from lib.utils import api_serialize_resource_obj
from lib.cache import get_object_from_pk
from conversations.templatetags.bleach_filter import bleach_filter
# from articles.api import PostMiniResource
from suites.models import Suite
from articles.models import Article
from links.models import Link
from suites.api import SuiteResource, SuiteMiniResource
from profiles.api import UserMiniResource
from django.utils.html import strip_tags
from tastypie.constants import ALL_WITH_RELATIONS
import json

from .sets import UserUnreadConvSet
from .models import Conversation, Post

class ConversationAuthorization(Suite101BaseAuthorization):
    def read_detail(self, object_list, bundle):
        return True
        # if not bundle.request.user.is_authenticated():
        #     return False
        # elif not bundle.request.user in bundle.obj.get_members():
        #     return False
        # return True

    def delete_detail(self, object_list, bundle):
        return True
        # return bundle.obj.owner == bundle.request.user or \
        #         bundle.request.user.is_moderator

    def update_detail(self, object_list, bundle):
        return True
        # return bundle.obj.owner == bundle.request.user or \
        #         bundle.request.user.is_moderator


class ConversationResource(Suite101Resource):
    owner = fields.ToOneField(UserMiniResource, 'owner')

    class Meta(Suite101Resource.Meta):
        data_cache_key = 'conv:full'  
        cache_authed = True          
        resource_name = 'conversation'
        queryset = Conversation.objects.filter()
        authorization = ConversationAuthorization()
        always_return_data = True
        list_allowed_methods = ['post', 'get']
        detail_allowed_methods = ['get', 'post', 'delete', 'put', 'patch']

        fields = [
            'id',
            'title',
        ]

        filtering = {
        }

    def dehydrate(self, bundle):
        conversation = bundle.obj        

        # bundle.data['owner'] = api_serialize_resource_obj(conversation.owner, UserMiniResource(), bundle.request)
        bundle.data['title'] = conversation.title
        bundle.data['any_title'] = conversation.get_conversation_title()
        bundle.data['member_count'] = conversation.get_member_count()        
        bundle.data['others'] = int(bundle.data['member_count']) - 5 if bundle.data['member_count'] and int(bundle.data['member_count']) > 5 else None
        bundle.data['hashed_id'] = conversation.get_hashed_id()
        return bundle


    def hydrate(self, bundle):
        if 'members' in bundle.data:
            del bundle.data['members']
        if 'posts' in bundle.data:
            del bundle.data['posts']
        if 'owner' in bundle.data:
            del bundle.data['owner']

        return bundle

    def obj_create(self, bundle, **kwargs):
        from chat.tasks import process_new_chat
        response = super(ConversationResource, self).obj_create(bundle, owner=bundle.request.user)
        # process_new_conversation(bundle.obj, bundle.request.user, bundle.request)
        return response

    def obj_update(self, bundle, **kwargs):
        response = super(ConversationResource, self).obj_update(bundle, **kwargs)
        bundle.obj.invalidate()
        return response

    def obj_delete(self, bundle, **kwargs):
        return super(ConversationResource, self).obj_delete(bundle, **kwargs)

class PostAuthorization(Suite101BaseAuthorization):
    def read_list(self, object_list, bundle):
        return True

    def create_detail(self, object_list, bundle):
        return True
        if bundle.request.user in bundle.obj.conversation.get_members():
            return True
        return True
        raise Unauthorized('You are not allowed to access that resource.')

    def delete_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user or \
                bundle.obj.conversation.owner == bundle.request.user or \
                bundle.request.user.is_moderator

    def update_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user or \
                bundle.request.user.is_moderator


class PostMiniResource(Suite101Resource):
    class Meta(Suite101Resource.Meta):
        resource_name = 'post_mini'
        data_cache_key = 'post:mini'    
        queryset = Post.objects.all().select_related('author')
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
        post = bundle.obj

        bundle.data['heading'] = post.get_heading()
        bundle.data['hash'] = post.get_hashed_id()
        bundle.data['obj_type'] = 'post'
        bundle.data['post_type'] = True

        try:
            bundle.data['created'] = time.mktime(post.created.timetuple())
        except:
            pass

        # bundle.data['author'] = api_serialize_resource_obj(post.author, UserMiniResource(), bundle.request)

        # year = datetime.datetime.now() - datetime.timedelta(days=365)
        # if post.created < year:
        #     bundle.data['year_old'] = True
        #     bundle.data['created_short'] = date(bundle.obj.created, "M j, Y")

        # bundle.data['is_published'] = post.published
        # bundle.data['draft'] = True if post.status == 'draft' else False
        # bundle.data['published'] = True if post.published else False
        
        bundle.data['heading'] = post.get_heading()
        try:
            bundle.data['excerpt'] = strip_tags(truncatechars(bleach_filter(post.body.excerpt, ['p']), 240))
        except:
            bundle.data['excerpt'] = 'Empty draft'

        # display_image = post.get_display_image()
        # if display_image:
        #     bundle.data['display_image'] = display_image.get_large_image_url()    
        
        # if post.tag_list:
        #     try:
        #         tags = post.tag_list
        #         if tags:
        #             tags = json.loads(tags.encode('utf-8'))
        #             tags_obj = [{'tag': '%s' % tag, 'tagUrl': '/q/%s' % (re.sub('[^0-9a-zA-Z]+', '-', tag).lower())} for tag in bundle.data['tags']]
        #             bundle.data['tag_list'] = tags_obj
        #     except Exception as e:
        #         pass

        return bundle

    def get_object_list(self, request):
        return super(PostMiniResource, self).get_object_list(request)

class PostResource(Suite101Resource):
    author = fields.ToOneField('profiles.api.UserMiniResource', 'author')
    conversation = fields.ToOneField(ConversationResource, 'conversation')
    reply_to = fields.ToOneField('self', 'reply_to', null=True)

    class Meta(Suite101Resource.Meta):
        resource_name = 'post'
        data_cache_key = 'post:full'
        cache_authed = True
        queryset = Post.objects.all().select_related('author')
        authorization = PostAuthorization()
        include_absolute_url = True
        allowed_methods = ['get', 'post', 'delete', 'put', 'patch']
        always_return_data = True

        fields = [
            'body',
            'id',
            'conversation',
            'created',
        ]

        filtering = {
            'conversation': 'exact',
            'created': 'gt',
        }
   
    def dehydrate(self, bundle):
        post = bundle.obj
        bundle.data['author'] = api_serialize_resource_obj(post.author, UserMiniResource(), bundle.request)
        bundle.data['created'] = post.created.strftime('%Y-%m-%d %H:%M:%S.%f')
        bundle.data['created_tuple'] = time.mktime(post.created.timetuple())
        bundle.data['recommends'] = int(post.get_recommend_count())

        if post.reply_to:
            bundle.data['reply_to'] = api_serialize_resource_obj(post.reply_to, PostResource(), bundle.request)
        return bundle

    def hydrate(self, bundle):
        if 'author' in bundle.data:
            del bundle.data['author']
        if 'created' in bundle.data:
            del bundle.data['created']
        return bundle

    def obj_create(self, bundle, **kwargs):
        response = super(PostResource, self).obj_create(bundle, author=bundle.request.user)
        import time
        start = time.time()
        
        from conversations.tasks import create_suite_post_objects, create_story_parent_object, update_story_word_counts
        # update the saved_on date
        bundle.data['saved_on'] = datetime.datetime.now()

        # in case slug is posted, remove it.
        if 'slug' in bundle.data:
            del bundle.data['slug']

        try:
            # clean up embeds we've removed
            embeds = bundle.data['embeds']
            # need to set the story field in all embed objects (initially created without a story)
            if embeds:
                for embed in embeds:
                    try:
                        embed_model = StoryEmbed.objects.get(pk=embed['id'])
                        embed_model.story = bundle.obj 
                        if not embed_model:
                            continue
                        if embed_model.content_type == ContentType.objects.get_for_model(ArticleImage):
                            embed_model.caption = embed['caption']
                            embed_model.content_object.credit = embed['embed_object']['credit']
                            embed_model.content_object.credit_link = embed['embed_object']['credit_link']                            
                            embed_model.content_object.save()
                        embed_model.save()                            
                    except Exception as e:
                        print('failed to save embed model meta data: %s' % e)

        except Exception as e:
            print(e)
            pass 

        try:
            # update user activity stats
            if 'words_changed' in bundle.data:
                if bundle.request.user.id == bundle.data['author']['id']:
                    update_story_word_counts(bundle.obj, bundle.data['words_changed'])
        except Exception as e:
            print(e)

        # try:
        #     if 'story_parent' in bundle.data:
        #         if bundle.data['story_parent']:
        #             create_story_parent_object(bundle.obj, bundle.data['story_parent'])
        # except Exception as e:
        #     print '--- error2: %s' % e

        # try:
        #     if 'suites' in bundle.data and bundle.data['suites']:
        #         create_suite_post_objects(bundle.obj, bundle.data['suites'])
        # except Exception as e:
        #     print '--- error3: %s' % e

        # # if the user is publishing this story, we do some post processing
        # if 'publish' in bundle.data and bundle.data['publish']:
        #     print 'about to hand off to post_publish...'
        #     _post_article_publish(bundle.obj)

        return response

    # def obj_create(self, bundle, **kwargs):
    #     response = super(PostResource, self).obj_create(bundle, user=bundle.request.user)
        
    #     return response

    def obj_delete(self, bundle, **kwargs):
        response = super(PostResource, self).obj_delete(bundle, **kwargs)
        return response

    # def obj_delete(self, bundle, **kwargs):
    #     """
    #     A ORM-specific implementation of ``obj_delete``.

    #     Takes optional ``kwargs``, which are used to narrow the query to find
    #     the instance.
    #     """
    #     """ copied from tastypie resources.py """
    #     from django.core.exceptions import ObjectDoesNotExist
    #     from tastypie.exceptions import NotFound
    #     if not hasattr(bundle.obj, 'delete'):
    #         try:
    #             bundle.obj = self.obj_get(bundle=bundle, **kwargs)
    #         except ObjectDoesNotExist:
    #             raise NotFound("A model instance matching the provided arguments could not be found.")
    #     bundle.obj.mark_deleted()
        
# class ConversationMemberAuthorization(Suite101BaseAuthorization):
#     def create_list(self, object_list, bundle):
#         return []
    
#     def create_detail(self, object_list, bundle):
#         if bundle.request.user.is_active:
#             # only the owner or a chat member or a moderator can add a chat member.
#             if bundle.obj.chat.owner == bundle.request.user or \
#                 bundle.request.user in bundle.obj.chat.get_members() or \
#                 bundle.request.user.is_moderator:
#                 return True
#             else:
#                 return Unauthorized()
#         else:
#             raise Unauthorized('Sorry, your account is inactive')

#     def delete_detail(self, object_list, bundle):
#         return bundle.obj.chat.owner == bundle.request.user or \
#                 bundle.obj.user == bundle.request.user or \
#                 bundle.request.user.is_moderator


# class ChatMemberResource(Suite101Resource):
#     user = fields.ToOneField(UserMiniResource, 'user')
#     chat = fields.ToOneField(ChatResource, 'chat')

#     class Meta(Suite101Resource.Meta):
#         resource_name = 'chat_member'
#         queryset = ChatMember.objects.all()
#         authorization = ConversationMemberAuthorization()
#         list_allowed_methods = ['get', 'post', 'put']
#         include_absolute_url = False
#         always_return_data = True

#         fields = [
#             'id',
#             'message',
#         ]

#         filtering = {
#             'chat': 'exact',
#             'user': 'exact',
#         }
   
#     def dehydrate(self, bundle):
#         print 'dehydrating member'
#         bundle.data['user'] = api_serialize_resource_obj(bundle.obj.user, UserMiniResource(), bundle.request)
#         return bundle

#     def obj_create(self, bundle, **kwargs):
#         print 'creating obj'
#         try:
#             from chat.tasks import process_new_chat_member
#             response = super(ChatMemberResource, self).obj_create(bundle, **kwargs)

#             try:
#                 request_user = bundle.request.user
#                 bundle_obj = bundle.obj
#             except Exception as e:
#                 print(e)
#             process_new_chat_member(bundle.obj)
#         except Exception as e:
#             print 'problem creating member: %s' % e

#         return response

#     def obj_delete(self, bundle, **kwargs):
#         import celery
#         response = super(ChatMemberResource, self).obj_delete(bundle, **kwargs)
#         # in case this member notification hasn't been sent yet, delete the task
#         celery.task.control.revoke(bundle.obj.celery_task_id)
#         return response


class ConversationMiniResource(Suite101Resource):
    owner = fields.ToOneField(UserMiniResource, 'owner')
    # members = fields.ToManyField(ChatMemberResource, 'members', null=True, readonly=True)

    def determine_format(self, request):
       return  'application/json'

    class Meta(Suite101Resource.Meta):
        data_cache_key = 'conv:mini'
        resource_name = 'conv_mini'
        queryset = Conversation.objects.all()
        authorization = ReadOnlyAuthorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        limit = 100

        filtering = {
            'owner': 'exact',
            'members': ALL_WITH_RELATIONS
        }

    def dehydrate(self, bundle):
        conversation = bundle.obj        

        bundle.data['title'] = conversation.title
        bundle.data['any_title'] = conversation.get_conversation_title()
        bundle.data['top_members'] = conversation.get_top_members(bundle.request)
        bundle.data['member_count'] = conversation.get_member_count()        
        bundle.data['others'] = int(bundle.data['member_count']) - 5 if bundle.data['member_count'] and int(bundle.data['member_count']) > 5 else None

        bundle.data['hashed_id'] = conversation.get_hashed_id()

        try:
            last_post = Post.objects.filter(conversation=conversation)[0]
            bundle.data['last_msg'] = strip_tags(bleach_filter(last_post.message, ['p']))
            bundle.data['last_msg_author'] = last_post.user.get_full_name()
            bundle.data['last_msg_auth_head'] = last_post.user.get_profile_image()
            bundle.data['last_msg_date'] = time.mktime(last_post.created.timetuple())
            bundle.data['last_msg_date_formatted'] = last_post.created.strftime('%a %b %d %H:%M:%S +0000 %Y')

        except:
            pass

        return bundle

    def get_object_list(self, request):
        if request.user.is_authenticated():
            chat_pks = request.user.chats.all().values_list('chat', flat=True)
            return super(ConversationMiniResource, self).get_object_list(request) | \
                    super(ConversationMiniResource, self).get_object_list(request).filter(pk__in=list(chat_pks))

        # if they aren't authenticated, we also check for things they were invited to
        elif 'invite_chat_auth' in request.session and request.session['invite_chat_auth']:
            return super(ConversationMiniResource, self).get_object_list(request) | \
                        super(ConversationMiniResource, self).get_object_list(request).filter(pk=request.session['invite_chat_auth'])

        else:
            return ""

# class ChatInviteValidation(Validation):
#     def is_valid(self, bundle, request=None):
#         if not bundle.data:
#             return {'__all__': 'No data?'}

#         errors = {}

#         # before we send out the invitation, make sure we haven't already sent one!
#         # don't spam people!!!!
#         if 'email' in bundle.data:
#             try:
#                 ChatInvite.objects.get(
#                     email__iexact=bundle.data['email'],
#                     chat=bundle.obj.chat
#                 )
#             except:
#                 pass
#             else:
#                 return {'__all__': 'Already invited this user'}

#         return errors

# class ChatInviteResource(Suite101Resource):
#     chat = fields.ToOneField(ChatResource, 'chat')

#     class Meta(Suite101Resource.Meta):
#         resource_name = 'chat_invite'
#         queryset = ChatInvite.objects.all()
#         authorization = ConversationMemberAuthorization()
#         validation = ChatInviteValidation()
#         include_absolute_url = False
#         always_return_data = True

#         fields = [
#             'message',
#             'email',
#         ]

#         filtering = {
#             'chat': 'exact'
#         }
   
#     def obj_create(self, bundle, **kwargs):
#         from chat.utils import send_chat_invite_notification
#         response = super(ChatInviteResource, self).obj_create(bundle, **kwargs)
#         send_chat_invite_notification(
#             bundle.request.user,
#             bundle.obj,
#             bundle.obj.chat,
#             bundle.obj.email,
#             bundle.obj.message
#         )
#         return response