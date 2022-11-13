import celery
import datetime
import json

from django.contrib.auth import get_user_model
from chat.models import Chat
from chat.utils import send_unread_chat_notification
from chat.sets import UserUnreadChatSet
from lib.enums import *

@celery.task(name='chat.tasks.process_new_chat_member')
def process_new_chat_member(chat_member):
    from chat.sets import UserUnreadChatSet
    from chat.models import ChatMessage

    # if the user is added manually (ie invited)
    if not ChatMessage.objects.filter(chat=chat_member.chat, user=chat_member.user).count(): 
        chat = chat_member.chat
        user = chat_member.user
        messages = chat.get_message_count()

        UserUnreadChatSet(user.pk).increment(chat.pk, messages)

@celery.task(name='chat.tasks.process_new_chat')
def process_new_chat(chat, user, request):
    import time
    from django.contrib.contenttypes.models import ContentType
    from suites.models import Suite, SuiteMember
    from articles.models import Article
    from chat.models import ChatMember

    time_score = time.mktime(chat.created.timetuple())
    # first make sure the user who creates the chat is a member
    try:
        ChatMember.objects.get_or_create(user=user, chat=chat)
    except Exception as e:
        print(e)
        pass
 

@celery.task(name='chat.tasks.recount_chat_stats')
def recount_chat_stats(chat_pk):
    from chat.models import ChatMember, ChatMessage
    from stats.sets import ChatStats
    
    try:
        members = ChatMember.objects.all().filter(chat__pk=chat_pk).count()
        ChatStats(chat_pk).set(members,"members")
    except:
        pass
    try:
        messages = ChatMessage.objects.all().filter(chat__pk=chat_pk).count()
        ChatStats(chat_pk).set(messages,"messages")
    except:
        pass

@celery.task(name='chat.tasks.process_new_chat_message')
def process_new_chat_message(message, request):
    import time
    from django.contrib.contenttypes.models import ContentType
    from chat.models import ChatMember, ChatMessage
    from chat.sets import ChatTeaser, ChatMessageSet, UserUnreadChatSet, UserChatNotifySet
    from articles.models import Article
    from chat.api import ChatMiniResource
    from lib.utils import api_serialize_resource_obj
    from lib.cache import get_object_from_pk    
    from lib.sets import RedisObject

    time_score = time.mktime(message.created.timetuple())

    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    chat = message.chat
    user = message.user
    chat_followers = []

    # All participants are members
    try:
        member, created = ChatMember.objects.get_or_create(chat=chat, user=user)
    except:
        pass

    chat.last_message_date = message.created
    recount_chat_stats(chat.pk)
    chat.invalidate()
    chat.save()
    chat.fanout_notification()  

@celery.task(name='chat.tasks.new_message_email')
def new_message_email(message):
    from project import settings as proj_settings
    from chat.sets import UserChatNotifySet
    from lib.tasks import send_email
    from lib.cache import get_object_from_pk
    from django.contrib.auth import get_user_model
    User = get_user_model()

    chat = message.chat
    emails = []
    template_name = 'emails/chat_unread_messages'
    user = message.user


    countdown = 300 #seconds

    # if user == chat.content_object.author:
        # template_name = 'somethingelse'
    
    context = {
        'user': user,
        'message_count': 12,
        'chat': message.chat,
        'message': message,
        'site_url': proj_settings.SITE_URL,
    }
    if message.chat.private:
        title = 'You\'ve received a new message on Suite'
    else:
        title = 'A new message has been posted on Suite' # work the discussion title into this
 
    members = chat.get_members()
    for member in members:
        if member.get_unread_chats(): # only proceed if the chat is still in the unread set
            send_it = UserChatNotifySet(member.pk).remove_from_set(chat.pk) # returns 1 if the chat existed; 0 if not
            if send_it:
                emails.append(member.email)
        
    send_email.apply_async(args=[emails, title, template_name, context], countdown=countdown)
    

############################
# ported from articles.tasks
############################


# @celery.task(name='articles.tasks.update_story_word_counts')
# def update_story_word_counts(story, count):
#     from lib.sets import RedisObject
#     from stats.sets import StoryDailyStatsWordsAdded, StoryDailyStatsWordsRemoved, UserDailyStatsWordsAdded, UserDailyStatsWordsRemoved
#     redis = RedisObject().get_redis_connection()
#     pipe = redis.pipeline()
#     user = story.author
#     # also keep track of global values here
#     if count > 0:
#         redis.pipeline(StoryDailyStatsWordsAdded(story.pk).increment(count))
#         redis.pipeline(UserDailyStatsWordsAdded(user.pk).increment(count))
#         redis.pipeline(UserDailyStatsWordsAdded('glo').increment(count))
#     elif count < 0:
#         redis.pipeline(StoryDailyStatsWordsRemoved(story.pk).increment(count))
#         redis.pipeline(UserDailyStatsWordsRemoved(user.pk).increment(abs(count)))
#         redis.pipeline(UserDailyStatsWordsRemoved('glo').increment(abs(count)))
#     pipe.execute()

# @celery.task(name='articles.tasks.resize_image')
# def resize_image(storyImage):
#     from articles.utils import resize_story_image
#     resize_story_image(storyImage)

# @celery.task(name='articles.tasks.refresh_alchemy')
# def refresh_alchemy(story):
#     from lib.alchemyapi import AlchemyAPI

#     alchemy_obj = AlchemyAPI()
#     alchemy_obj._apiKey = settings.ALCHEMY_API_KEY

#     keyword_results = {}
#     entity_results = {}
#     process = False
#     content = strip_tags(story.body.content)

#     RELEVANCE_THRESHOLD = .6
#     story.keyword_list = []
#     story.entity_list = []
#     story.alchemy_keyword_str = ''
#     story.alchemy_entity_str = ''

#     try:
#         keyword_results = alchemy_obj.keywords("text", content)
#         if not keyword_results['status']=="ERROR":
#             keyword_str = keyword_results
#             if keyword_str:
#                 process = True
#                 objects = keyword_str['keywords']
#                 if objects:
#                     for obj in objects:
#                         kw = str(obj['text'])
#                         relevance = float(obj['relevance'])
#                         if relevance > RELEVANCE_THRESHOLD:
#                             story.keyword_list.append(kw)
#                     if story.keyword_list:
#                         story.keyword_list = json.dumps(story.keyword_list)

#     except Exception as e:
#         pass

#     try:
#         entity_results = alchemy_obj.entities("text", content)
#         if not entity_results['status']=="ERROR":
#             entity_str = entity_results
#             process = True
#             if entity_str:
#                 objects = entity_str['entities']
#                 if objects:
#                     for obj in objects:
#                         entity = str(obj['text'])
#                         relevance = float(obj['relevance'])
#                         if relevance > RELEVANCE_THRESHOLD:
#                             story.entity_list.append(entity)
#                     if story.entity_list:
#                         story.entity_list = json.dumps(story.entity_list)                            
#     except:
#         pass

#     if process:
#         story.alchemy_keyword_str = json.dumps(keyword_str)                        
#         story.alchemy_entity_str = json.dumps(entity_str)
#         story.save()
#         story.invalidate()

# @celery.task(name='articles.tasks.prune_story_embeds')
# def prune_story_embeds(story, embeds_json):
#     ''' clear out embeds user has removed client-side '''
#     from articles.models import Article, StoryEmbed
#     embed_pks = [obj['id'] for obj in embeds_json]
#     embeds = StoryEmbed.objects.filter(story=story).exclude(pk__in=list(embed_pks))
#     if embeds:
#         for embed in embeds:
#             embed.invalidate()
#             embed.delete()

# @celery.task(name='articles.tasks.refresh_recommended_stories')
# def refresh_recommended_stories():
#     from articles.models import Article
#     from lib.sets import RedisObject

#     redis = RedisObject().get_redis_connection(slave=False)
#     pipe = redis.pipeline()  

#     # Featured stories
#     stories = Article.objects.published().filter(featured__isnull=False, author__is_active=True)
#     if stories:
#         for story in stories:
#             date = int(time.mktime(story.created.timetuple()))
#             redis.pipeline(RecommendedStoriesSet().add_to_set(story.pk))

#         pipe.execute()
    

# @celery.task(name='articles.tasks.create_story_parent_objects')
# def create_story_parent_object(story, parent):
#     # build parent object after client-side story create/edit
#     from lib.cache import get_object_from_pk
#     from suites.tasks import refresh_suite_stats
#     from articles.models import Article, StoryParent
#     from suites.models import Suite
#     from links.models import Link
#     from lib.sets import RedisObject

#     redis = RedisObject().get_redis_connection(slave=False)
#     pipe = redis.pipeline()   

#     try:
#         object_id = int(parent['id'])
#         object_type = parent['obj_type']
#     except Exception as e:
#         print(e)
#         pass

#     try:
#         if object_type == 'story':
#             print 'this is a story'
#             obj_type = Article
#         if object_type == 'link':
#             print 'this is a link'
#             obj_type = Link

#         parent_object = get_object_from_pk(obj_type, object_id, False)  

#     except Exception as e:
#         print(e)

#     # Create the StoryParent object
#     parent, created = StoryParent.objects.get_or_create(story=story)
#     parent.content_object = parent_object
#     parent.invalidate()
#     parent.save()

# @celery.task(name='articles.tasks.create_suite_post_objects')
# def create_suite_post_objects(content_object, suites, request=None, reply=False):
#     ''' build SuitePost objects after client-side story create/edit '''
#     from lib.cache import get_object_from_pk
#     from suites.models import Suite, SuitePost
#     from articles.models import Article
#     from links.models import Link

#     def remove_suite_post(suite_pk):
#         try:
#             suite = get_object_from_pk(Suite, suite_pk, False)  
#         except Exception as e:
#             print(e)
#             pass

#         try:
#             suite_posts = SuitePost.objects.filter(suite=suite, content_type=ContentType.objects.get_for_model(content_object), object_id=content_object.pk).delete()
#             if suite_posts:
#                 for ss in suite_posts:
#                     ss.invalidate
#                     ss.delete()
#         except Exception as e:
#             print 'failed to get suite post object: %s' % e
#             pass

#     def add_suite_post(suite_pk):
#         try:
#             suite = get_object_from_pk(Suite, suite_pk, False)  
#             suite_post, created = SuitePost.objects.get_or_create(suite=suite, content_type=ContentType.objects.get_for_model(content_object), object_id=content_object.pk)
#             suite_post.added_by = request.user
#             suite_post.save()
#             added.append(suite_post.suite.name)
#             fanout_add_to_suite(suite_post)
#         except Exception as e:
#             pass

#     suite_pks = []
#     for suite in suites:
#         suite_pks.insert(0, str(suite['id']))

#     # remove any suites that have been edited away
#     to_remove = []
#     existing_suites = story.get_story_suite_pks(request=None, all=True)
#     for es in existing_suites:
#         if str(es) not in suite_pks:
#             remove_suite_post(str(es))
                
#     # process new/current ones
#     for suite_pk in suite_pks:
#         add_suite_post(suite_pk)

# @celery.task(name='articles.tasks.update_tag_sets')
# def update_tag_sets(story):
#     from lib.sets import RedisObject
#     from articles.tag_sets import AllTagSet, TagStorySet
#     import json
#     redis = RedisObject().get_redis_connection()
#     pipe = redis.pipeline()

#     tags = json.loads(str(story.tag_list))

#     for tag in tags:
#         # key = spaceless tags
#         spaceless_tag = "".join(tag.split())
#         redis.pipeline(AllTagSet().add_to_set(tag))
#         redis.pipeline(TagStorySet(spaceless_tag).add_to_set(story.pk))
#     pipe.execute()

# @celery.task(name='articles.tasks.update_word_count')
# def update_story_scores(story):

#     # Update word count    
#     story.word_count = story.get_word_count(True)
#     story.save()
#     story.invalidate()

# @celery.task(name='articles.tasks.fanout_new_story')
# def fanout_new_story(story):
#     import datetime
#     import time
#     from lib.cache import get_object_from_pk
#     from suites.models import Suite
#     from dateutil import parser
#     from articles.sets import UserMainStoryFeed
#     from lib.sets import RedisObject

#     redis = RedisObject().get_redis_connection(slave=False)
#     pipe = redis.pipeline()

#     time_score = time.mktime(story.created.timetuple())
#     fanout_list = [story.author.pk]

#     try:
#         story.fanout_notification()
#     except Exception as e:
#         print '-------- problem fanning out:; %s' % e

#     followers = story.author.get_follower_pks()
#     if followers:
#         for follower_pk in story.author.get_follower_pks():
#             if not follower_pk in fanout_list:
#                 fanout_list.append(follower_pk)

#     suite_pks = story.get_story_suite_pks(None, fetch_all=True )
#     if suite_pks:
#         for pk in suite_pks:
#             try:
#                 suite = get_object_from_pk(Suite, pk, False)

#                 if suite.private:
#                     suite_members = list(suite.get_member_pks() or [])
#                     for pk in suite_members:
#                         if pk not in fanout_list:
#                             fanout_list.append(pk)

#                 else:
#                     suite_followers = list(suite.get_follower_pks() or [])
#                     user_followers = list(user.get_follower_pks() or [])

#                     for pk in suite_followers + user_followers:
#                         if pk not in fanout_list:
#                             fanout_list.append(pk)

#             except:
#                 pass
                 
#     if fanout_list:
#         for fanny in fanout_list:
#             redis.pipeline(UserMainStoryFeed(fanny).add_to_set(story.pk, time_score))  
#         pipe.execute()
        
# @celery.task(name='articles.tasks.refresh_story_stats')
# def refresh_story_stats():
#     from django.contrib.contenttypes.models import ContentType
#     from lib.utils import get_serialized_list, queryset_iterator
#     from stats.sets import StoryStats
#     from articles.models import Article

# @celery.task(name='articles.tasks.eradicate_story')
# def purge_deleted_story(story):
#     ''' Clean up after a 'deleted' story. '''
#     from django.contrib.contenttypes.models import ContentType
#     from lib.cache import get_object_from_pk
#     from articles.sets import RecommendedStoriesSet
#     from suites.tasks import refresh_suite_stats
#     from suites.models import Suite, SuitePost
#     from lib.sets import RedisObject

#     # TODO: REMOVE FROM ACTIVITY FEED

#     # # Followers' main story feeds
#     # followers = story.author.get_follower_pks()
#     # if followers:
#     #     for follower in followers:
#     #         print 'remove from feed!'

#     suite_posts = SuitePost.objects.filter(content_type=ContentType.objects.get_for_model(story), object_id=story.pk)
#     if suite_posts:
#         for sp in suite_posts:
#             sp.suite.invalidate()
#             sp.delete()

#     # Clear parents, children
#     if story.parent_is_story():
#         parent = story.parent_obj
#         parent.invalidate()

#     children = story.get_response_pks()
#     if children:
#         for child in children:
#             child_obj = get_object_from_pk(Article, child, False)
#             child_obj.invalidate()

# @celery.task(name='articles.tasks.unpublish_story')
# def unpublish_story(story):
#     import datetime
#     from suites.models import Suite
#     from stats.tasks import process_local_stats_event
#     from articles.sets import RecommendedStoriesSet
#     from suites.tasks import refresh_suite_stats
#     from lib.sets import RedisObject
#     from lib.utils import task_ready

#     redis = RedisObject().get_redis_connection(slave=False)
#     pipe = redis.pipeline()
#     task_ready('sitemaps', 1)

#     if story.featured:
#         story.featured = None;
#         story.save()

#     # invalidate recommended stories cache
#     RecommendedStoriesSet().clear_set()

#     stat_value = -1
#     event = {
#         "event": "stories",
#         "date": story.created.strftime("%Y-%m-%d"),
#         "value": stat_value,
#         "story": story.pk,
#         "author": story.author.pk,
#         }
#     process_local_stats_event(event)

#     if story.parent_is_story():
#         parent = story.parent_obj
#         # Add a few fields to the event string
#         event['event'] = "responses"
#         event['parent'] = parent.pk
#         event['parent_auth'] = parent.author.pk
#         event['responder'] = story.author.pk
#         process_local_stats_event(event)

#     story.author.reset_last_published_date()


# @celery.task(name='articles.tasks.post_publish')
# def post_publish(story):
#     import time
#     from lib.utils import queryset_iterator, task_ready
#     from lib.tasks import send_email_alert, user_index_check
#     from profiles.tasks import refresh_user_stories_counts
#     from articles.tasks import fanout_new_story, update_tag_sets, refresh_alchemy
#     from articles.models import Article
#     from stats.tasks import process_local_stats_event

#     print 'welcome to post publish'
#     author = story.author
#     refresh_user_stories_counts(author)
#     try:
#         ip = str(story.author.last_known_ip)
#     except:
#         ip = ""

#     stat_value = 1
#     event = {
#         "event": "stories",
#         "date": story.created.strftime("%Y-%m-%d"),
#         "value": stat_value,
#         "ip": ip,
#         "story": story.pk,
#         "author": story.author.pk,
#         }
#     try:
#         process_local_stats_event(event)
#     except Exception as e:
#         print(e)

#     update_tag_sets(story)
#     refresh_alchemy(story)    

#     if story.parent_is_story():
#         parent = story.parent_obj

#         # build the event json string
#         event['event'] = "responses"
#         event['parent'] = parent.pk
#         event['parent_auth'] = parent.author.pk
#         event['responder'] = story.author.pk
#         process_local_stats_event(event)

#         # parent.save()
#         parent.invalidate()
        
#         parent.fanout_notification()

#     if story.author.approved:
#         # OK to generate sitemaps next time through
#         task_ready('sitemaps', 1)
    
#     fanout_new_story(story)
#     if story.parent_is_story():
#         parent = story.parent_obj
#         send_email_alert(parent.author, story, author)

#     # story.get_word_count(update=True)
#     user_index_check(story.author)
#     author.last_pub_date = story.created

#     # save the author to rebuild his search index entry
#     author.invalidate()
#     author.save()


# @celery.task(name='articles.tasks.update_published_story')
# def update_published_story(story):
#     from profiles.tasks import refresh_user_stories_counts, refresh_user_tags
#     from lib.tasks import user_index_check
#     from suites.tasks import refresh_suite_tags

#     try:
#         story.get_word_count(update=True)
#     except:
#         pass

#     try:
#         refresh_alchemy(story)
#     except Exception as e:
#         pass

#     try:
#         refresh_suite_tags(story)
#         refresh_user_tags(story.author)
#     except Exception as e:
#         pass

#     if story.tag_list:
#         update_tag_sets(story)

#     user_index_check(story.author)


# @celery.task(name='articles.tasks.check_copyscape')
# def check_copyscape(article):
#     from lib.utils import strip_non_ascii
#     from articles.copyscape import copyscape_api_text_search_internet

#     # import pdb; pdb.set_trace()

#     content = strip_tags(article.body.content)
#     content = str(strip_non_ascii(content))

#     response = copyscape_api_text_search_internet(content, "UTF-8")
#     try:
#         result_count = int(response.find('count').text)
#     except:
#         print 'error - count %s' % response.find('count').text
#         return

#     if result_count <= 0:
#         # hmmmm???? no results? something's wrong!!!
#         print 'How is result count zero???'
#     elif result_count == 1:
#         # ok this is normal... let's make sure it's our copy
#         result = response.find('result')
#         url = result.find('url').text
#         if not article.get_absolute_url() in url:
#             print 'URL of one match is not ours?? %s' % url
#             # what do we do here?

#     else:
#         results = response.findall('result')

#         for result in results:
#             url = result.find('url').text
#             if article.get_absolute_url() in url:
#                 continue
#             try:
#                 matched_words = int(result.find('minwordsmatched').text)
#             except:
#                 continue

#             ratio = float(matched_words) / float(article.word_count)
#             if ratio > 0.5:
#                 article.external_canonical = url
#                 article.save()    