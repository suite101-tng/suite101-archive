import random
import json
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.core.urlresolvers import reverse
from lib.cache import get_object_from_pk, invalidate_object
from django.contrib.auth import get_user_model
from hashlib import sha1 as sha_constructor
from random import randint
from django.utils.html import strip_tags
from articles.templatetags.bleach_filter import bleach_filter
from django.template.defaultfilters import wordcount, truncatechars, slugify
from model_utils.fields import SplitField
from suites.models import Suite
from links.models import Link
from notifications.models import Notification
from lib.utils import get_serialized_list, generate_hashed_id, diff

from model_utils import Choices
from model_utils.models import TimeStampedModel

from lib.enums import HASH_TYPE_CONVERSATION, HASH_TYPE_POST
User = settings.AUTH_USER_MODEL

class Conversation(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owner_conversations')
    private = models.BooleanField(default=True)
    hashed_id = models.CharField(blank=True, max_length=50, db_index=True)
    archive_pk = models.IntegerField(blank=True, db_index=True, default=0)

    # conversation from which this has branched off
    conversation_parent = models.ForeignKey('conversations.Post', related_name='child_conversations', blank=True, null=True, on_delete=models.SET_NULL)

    last_post_date = models.DateTimeField(db_index=True, null=True)
    title = models.CharField(blank=True, max_length=500, default='')
    description = models.CharField(max_length=255, blank=True)
    notification_object = GenericRelation(Notification)    

    class Meta:
        ordering = ['-modified']

    class CacheKey:
        obj_cache_key = 'conv:obj'

    def delete(self, *args, **kwargs):
        self.invalidate()
        return super(Conversation, self).delete(*args, **kwargs)

    def get_member_count(self):
        return ConversationMember.objects.all().filter(conversation=self).count()

    def get_member_pks(self):
        ''' Return a list of pks, recent posters first'''
        from .sets import ConversationMembers
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection()
        pipe = redis.pipeline()   

        member_pks = ConversationMembers(self.pk).get_full_set()
        if not member_pks:
            member_pks = []            
            posters = Post.objects.all().filter(conversation=self).values_list('author__pk', flat=True).order_by('-created').distinct()
            conv_members = ConversationMember.objects.all().filter(conversation=self).values_list('user__pk', flat=True).distinct()

            if posters:
                for poster in posters:
                    if not poster in member_pks:
                        member_pks.append(poster)

            if conv_members:
                for mem in conv_members:
                    if not mem in member_pks:
                        member_pks.append(mem)
            
            if not member_pks:
                return None

            i = 0 
            for member in member_pks:
                redis.pipeline(ConversationMembers(self.pk).add_to_set(member,i))
                redis.pipeline(ConversationMembers(self.pk).expire(settings.DEFAULT_CACHE_TIMEOUT))
                i += 1
            pipe.execute()
        return member_pks

    def get_top_members(self, request=None):       
        member_pks = self.get_member_pks()
        if not member_pks:
            return None

        if not request:
            request = HttpRequest()     

        MEMBERS_SHOWN = 3
        num_members = len(member_pks)

        mems = get_serialized_list(request, member_pks[:MEMBERS_SHOWN], 'user:mini')
        others = num_members - MEMBERS_SHOWN if num_members and num_members > MEMBERS_SHOWN else 0
        response = {
            'topMemberHeads': mems,
            'others': others,
            'lone': True if num_members < 2 else False
        }
        return json.dumps(response)


    def get_post_count(self):
        try:
            return Post.objects.all().filter(conversation=self).count()
        except:
            return 0

    def get_conversation_title(self):
        if self.title:
            return self.title
        return "Untitled discussion"

    def get_absolute_url(self):
        try:
            return reverse('conversation_detail', kwargs={'hashed_id': self.get_hashed_id()})
        except:
            pass
        return ''

    def get_hashed_id(self):
        if not self.hashed_id:
            self.hashed_id = generate_hashed_id(self.owner.pk, HASH_TYPE_CONVERSATION, self.pk)
            self.save()
        return self.hashed_id

    def get_posts(self, request, page=None):
        from conversations.api import PostResource
        CONV_PAGINATION_LIMIT = 10
        
        all_posts = self.posts.all().order_by('-posted_on').values_list('pk', flat=True)
        more_posts = False
        posts_array = []

        if page:
            page = int(page)
            start = (page - 1) * CONV_PAGINATION_LIMIT
            end = page * CONV_PAGINATION_LIMIT
            posts = all_posts[start:end]
            if len(posts) > end:
                more_posts = True
            rev_posts = reversed(posts)
        else:
            posts = all_posts

        ordering = []
        posts_array = get_serialized_list(request, posts, 'post:mini')        
        # for post in posts:
        #     post_json = api_serialize_resource_obj(post, PostResource(), request)
        #     print('----------------------- post object: %s' % post_json)
        #     try:
        #         ordering.append(post.pk)
        #         posts_array.append(post_json)
        #     except Exception as e:
        #         pass

        return posts_array, more_posts

    def get_members(self):
        return [member.user for member in self.members.filter(user__is_active=True)]

    def viewer_is_member(self, user):
        if not user.is_authenticated():
            return False
        return user in self.get_members()

    def get_invites(self):
        return self.invited.exclude(auth_key='')

    def invalidate(self):
        invalidate_object(self)

    def show_ads(self, request=None):
        if request and request.user.is_authenticated():
            return False
        if self.ads_override == "hide":
            return False
        if self.ads_override == "show":
            return True
        if not self.author.ads_enabled:
            return False            
        # todo: add user ad preferences 
        return True if self.word_count and self.word_count > 200 else False        

    def fanout_notification(self):
        ''' fan out a notification for this conversation '''
        from notifications.utils import new_notification

        try:
            last_post = self.messages.all()[0]
            if not last_post:
                return
            fanout_list = [last_post.user]
            date = last_post.created
        except:
            return

        members = self.get_members() 
        if not members:
            return
        for mem in members:
            if not mem == last_post.user and not mem in fanout_list:
                fanout_list.append(mem)

        new_notification(self, fanout_list, date=date, conversation_type=True)

class ConversationMember(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='member_conversations')
    STATUS = Choices('active', 'moderator', 'blocked')
    status = models.CharField(choices=STATUS, default=STATUS.active, max_length=20)
    notification_target = GenericRelation(Notification)  

    class Meta:
        ordering = ['created']
        unique_together = ('conversation', 'user')

    class CacheKey:
        obj_cache_key = 'conv:member:obj'

    def invalidate(self):
        invalidate_object(self)   

class ConversationInvite(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, related_name='invited')
    email = models.EmailField(max_length=255)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created']

class PostManager(models.Manager):
    def published(self):
        return super(PostManager, self).all().filter(status=Post.STATUS.published)
    def drafts(self):
        return super(PostManager, self).all().filter(status=Post.STATUS.draft)

class PostRecommend(TimeStampedModel):
    post = models.ForeignKey('conversations.Post', related_name='recommends')
    user = models.ForeignKey(User, related_name='user_post_recommends', db_index=True)   

class PostEmbed(TimeStampedModel):
    ''' Can be any object (eg link, image, post) '''
    post = models.ForeignKey('conversations.Post', related_name='embeds', null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')    

    caption = models.CharField(max_length=512, blank=True)
    spill = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.invalidate()
        self.content_object.invalidate()

        super(PostEmbed, self).save(*args, **kwargs) 

    def invalidate(self):
        invalidate_object(self)  

class Post(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, related_name='posts', null=True, blank=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(User, related_name='posts', db_index=True)   
    posted_on = models.DateTimeField(null=True, db_index=True)
    reply_to = models.ForeignKey('conversations.Post', null=True, related_name='replies', blank=True, on_delete=models.SET_NULL)

    title = models.CharField(max_length=255, blank=True)
    body = SplitField(blank=True)
    word_count = models.IntegerField(default=0)

    story_dup = models.BooleanField(default=False)
    original_source = models.URLField('Source', blank=True)

    # response from AlchemyAPI fetch on save/create:
    alchemy_entity_str = models.TextField(blank=True)
    alchemy_keyword_str = models.TextField(blank=True)    
    # extracted from AlchemyAPI objects above
    entity_list = models.TextField(blank=True)
    keyword_list = models.TextField(blank=True)
    # user-input tags
    tag_list = models.TextField(blank=True)

    STATUS = Choices('draft', 'published', 'deleted')
    status = models.CharField(choices=STATUS, default=STATUS.draft,
                              max_length=20, db_index=True)

    hashed_id = models.CharField(blank=True, max_length=50, db_index=True)
       
    notification_object = GenericRelation(Notification)    

    objects = PostManager()

    class Meta:
        verbose_name_plural = "Posts"
        ordering = ['-created']

    class CacheKey:
        obj_cache_key = 'post:obj'

    def __unicode__(self):
        return '%s (%s)' % (self.title, self.pk)

    def get_absolute_url(self):
        # return self.get_hashed_id()
        return reverse('post_detail', kwargs={'author': self.author.slug, 'hashed_id': self.get_hashed_id()})

    def save(self, *args, **kwargs):
        self.title = self.title.strip()
        return super(Post, self).save(*args, **kwargs)

    @property
    def published(self):
        return self.status == self.STATUS.published

    @property
    def draft(self):
        return self.status == self.STATUS.draft

    @property
    def deleted(self):
        return self.status == self.STATUS.deleted

    def get_recommend_count(self):
        return self.recommends.filter(user__is_active=True).count()

    def get_heading(self):
        title = self.title
        if not title:
            title = strip_tags(truncatechars(bleach_filter(self.body.excerpt, ['p']), 60))
        return title

    def get_hashed_id(self):
        if not self.hashed_id:
            self.hashed_id = generate_hashed_id(self.author.pk, HASH_TYPE_POST, self.pk)
            self.save()
        return self.hashed_id

    def get_display_image(self):
        embeds = self.embeds.filter(story=self, content_type=ContentType.objects.get_for_model(ArticleImage))
        if not embeds:
            return None
        cover = embeds.filter(cover=True)
        if cover:
            return cover[0].content_object
        for embed in embeds:
            try:
                if embed.content_object.image.width > 600:
                    return embed.content_object
            except Exception as e:
                print('problem looping through story images: %s' % e)
                pass
        return None        

    def get_amalgamated_tags(self):
        amalgamated_tags = []
        tags = self.tag_list
        entities = self.entity_list
        keywords = self.keyword_list
  
        for tag_group in [tags, keywords, entities]:
            if tag_group:
                try:
                    tags = json.loads(tag_group)
                except:
                    continue
                for tag in tags:
                    print('tag: %s' % tag)
                    if not str(tag) in amalgamated_tags:
                        amalgamated_tags.append(str(tag))            

        return amalgamated_tags

    def tweet_params_encoded(self):
        import urllib
        user = '@%s' % self.author.twitter_username if self.author.twitter_username else self.author.get_full_name()
        if self.author.approved:
            text = '"%s" by %s via @suiteio' % (self.title, user)
        else:
            text = '"%s" by %s' % (self.title, user)

        data = {
            'url': '%s/%s' % (settings.SITE_URL, self.get_hashed_id()),
            'text': text.encode('utf-8', 'ignore')
        }
        return urllib.urlencode(data)

    def get_jsonld(self, request):
        from articles.sets import StoryJsonLd
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection()
        pipe = redis.pipeline()   

        json_ld = StoryJsonLd(self.pk).mget()[0]
        if json_ld:
            return json_ld
        else:
            story = self
            author_twitter = "https://twitter.com/%s" % story.author.twitter_username if story.author.twitter_username else ''
            author_facebook = story.author.facebook_url if story.author.facebook_url else ''
            suite_twitter = "https://twitter.com/suiteio"
            suite_facebook = "https://facebook.com/suitestories"
            try:
                # TODO: amalgamated_tags
                tags = json.loads(story.tag_list)
            except:
                tags = []
            try:
                cover = story.get_story_cover()
                large_image = cover.content_object.get_large_image_url()
                small_image = cover.content_object.get_small_image_url()
            except:
                image = ''
                large_image = ''
                small_image = ''
            try:
                suite = self.get_primary_suite(request)
                suite_name = suite['name']
                suite_url = suite['absoluteUrl']
            except:
                suite = None
                suite_name = ''
                suite_url = ''
            story_title = story.title if story.title and not story.title == 'Untitled' else ''
            try:
                subtitle = story.subtitle.strip() if story.subtitle else strip_tags(truncatechars(bleach_filter(story.body.excerpt, ['p']), 280))
            except:
                subtitle = ''

            json_ld = {
                "@context":"http://schema.org",
                "@type":"SocialMediaPosting",
                "name":"%s" % story_title,
                "headline":"%s" % story_title,
                "alternativeHeadline":"%s" % subtitle,
                "description":"%s" % subtitle,
                "url":"https://suite.io%s" % story.get_absolute_url(),
                "author":{
                    "@type":"Person",
                    "name":"%s" % story.author.get_full_name(),
                    "url":"https://suite.io%s" % story.author.get_absolute_url(),
                    "sameAs":[ author_twitter, author_facebook ]
                    },
                "creator":[story.author.get_full_name()],
                "dateCreated":story.created.strftime('%a %b %d %H:%M:%S +0000 %Y'),
                "datePublished":story.created.strftime('%a %b %d %H:%M:%S +0000 %Y'),
                "image": large_image,
                "thumbnailUrl": small_image,
                "articleSection":suite_name,
                "keywords":tags,
                "inLanguage":"en-us",
                "publisher": {
                    "@type":"Organization",
                    "name":"Suite",
                    "logo":"",
                    "sameAs":[ suite_facebook, suite_twitter ],
                    "url":"https://suite.io",
                    "founder":{"@type":"Person","name":"Michael Kedda"}
                    },
                "location":{"@type":"PostalAddress","addressLocality":"Vancouver","addressRegion":"BC"}
                }
            # try:
            #     if suite:
            #         breadcrumb_json_ld = {
            #                 "@context": "http://schema.org",
            #                 "@type": "BreadcrumbList",
            #                 "itemListElement":
            #                 [
            #                     {
            #                         "@type": "ListItem",
            #                         "position": 1,
            #                         "item":
            #                         {
            #                         "@id": "https://suite.io%s" % suite_url,
            #                         "name": "%s" % suite_name
            #                         }
            #                     }
            #                 ]
            #             }
            #         json_ld.append(breadcrumb_json_ld)

            # except Exception as e:
            #     pass

            if not json_ld:
                return None        

            redis.pipeline(StoryJsonLd(self.pk).set_key(json.dumps(json_ld)))                
            redis.pipeline(StoryJsonLd(self.pk).expire(settings.DEFAULT_CACHE_TIMEOUT))
            pipe.execute()

        return json.dumps(json_ld) 
                     
    def get_social_counts(self):
        import requests, json, urllib
        from urllib.parse import urlparse
        url = '%s/%s' % (settings.SITE_URL, self.get_absolute_url()),

        twitter_api_url = 'http://urls.api.twitter.com/1/urls/count.json?url=%s' % url

        facebook_query_encoded = 'SELECT%20total_count%20FROM%20link_stat%20WHERE%20url%20='
        facebook_graph_url = 'https://graph.facebook.com/fql?q=%s"%s"' % (facebook_query_encoded, url)

        tweet_counts = requests.get(twitter_api_url).json()
        facebook_counts = requests.get(facebook_graph_url).json()
        return tweet_counts, facebook_counts        