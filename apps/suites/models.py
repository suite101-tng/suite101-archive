from django.db import models
from django.db.models import Q   
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import json, time

# use AUTH_USER_MODEL here to prevent circular import
from project.settings import AUTH_USER_MODEL
from model_utils.fields import AutoLastModifiedField
from project import settings
from autoslug import AutoSlugField
from lib.models import Follow
from lib.utils import api_serialize_resource_obj, delete_all_images, get_serialized_list, generate_hashed_id
from lib.cache import invalidate_object
from lib.enums import *
from notifications.models import Notification
from notifications.utils import new_notification
from model_utils import Choices
from model_utils.models import TimeStampedModel
from lib.sets import RedisObject


class Suite(TimeStampedModel):
    """ A suite is a collection of articles with a single owner but multiple members """
    name = models.CharField(max_length=255, db_index=True)
    owner = models.ForeignKey(AUTH_USER_MODEL, related_name='owner_suites')
    slug = AutoSlugField(max_length=100, populate_from='name', unique=True, db_index=True, editable=True)
    about = models.TextField()
    description = models.CharField(max_length=140, blank=True, null=True)
    private = models.BooleanField(default=False)   
    hero_image = models.ForeignKey('suites.SuiteImage', blank=True, null=True, related_name='suite_hero')

    followers = GenericRelation(Follow)
    featured = models.DateTimeField(null=True, blank=True)
    hashed_id = models.CharField(blank=True, max_length=50, db_index=True)
    tag_list = models.TextField(blank=True)
    notification_object = GenericRelation(Notification)    

    class Meta:
        ordering = ['-modified', '-created']

    class CacheKey:
        obj_cache_key = 'suite:obj'

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        return super(Suite, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('suite_detail', kwargs={'hashed_id': self.get_hashed_id()})

    def get_short_url(self):
        return '/%s' % self.get_hashed_id()

    @property
    def member_count(self):
        return self.members.all().count()

    @property
    def follower_count(self):
        return self.get_followers_count()

    @property
    def story_count(self):
        return self.get_stories_count()

    def fanout_notification(self):
        ''' fan out a notification to suite.owner's followers on create '''
        User = get_user_model()       

        fanout_list = []

        # testing
        fanout_list = [User.objects.get(pk=7444)]

        followers = self.owner.get_follower_objects()
        if followers:
            for follower in followers:
                if not follower in fanout_list:
                    fanout_list.append(follower)

        new_notification(self, fanout_list)

    def get_hashed_id(self):
        if not self.hashed_id:
            self.hashed_id = generate_hashed_id(self.owner.pk, HASH_TYPE_SUITE, self.pk)
            self.save()
        return self.hashed_id

    def get_suite_tags(self):
        tags_output = ''
        tags = str(self.tag_list)
        split_tags = tags.split(',')
        for tag in split_tags:
            tags_output += ' %s' % str(tag)
        return tags_output

    def get_hero_image(self, request):
        if self.hero_image:
            from suites.api import SuiteImageResource
            return api_serialize_resource_obj(self.hero_image, SuiteImageResource(), request)
        return None        

    def get_suite_post_pks(self, request, page=1):
        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()
        pks = []
        cache_key = 'suite:posts:%s' % self.pk

        start = DEFAULT_PAGE_SIZE * (page - 1)
        stop = (page * DEFAULT_PAGE_SIZE) - 1
        pks = redis.zrevrange(cache_key, start, stop)

        if not pks and not page > 1:
            posts = SuitePost.objects.all().filter(suite=self)
            if posts:
                redis = RedisObject().get_redis_connection(slave=False)
                for post in posts:
                    if post.content_object.status=='published':
                        redis.zrevrange(cache_key, start, stop)
                        pks.append(post.pk)
                        created = time.mktime(post.created.timetuple())
                        pipe.zadd(cache_key, post.pk, created)
                pipe.expire(cache_key, settings.DEFAULT_CACHE_TIMEOUT)
                pipe.execute()
        if pks:
            pks = pks[start:stop]
        return pks


    def get_suite_posts(self, request, page=1):  
        from lib.utils import get_serialized_list 
        
        page = int(page)
        start = (page - 1) * DEFAULT_PAGE_SIZE
        end = page * DEFAULT_PAGE_SIZE

        try:
            post_pks = SuitePost.objects.all().filter(suite=self, post__status='published').values_list('content_id', flat=True)[start:end]
            suite_posts = get_serialized_list(request, post_pks, 'story:mini')
        except Exception as e:
            print(e)
            return None
        
        return suite_posts

    def expire_stats_key(self, key):
        from stats.sets import SuiteStats
        SuiteStats(self.pk).delete(key)

    def get_followers_count(self):
        return int(self.get_suite_stats(['followers'])['followers'])

    def get_stories_count(self):
        return int(self.get_suite_stats(['stories']))
        
    # Get a dictionary with core suite stats
    def get_suite_stats(self, attrs=[]):
        from lib.models import Follow
        from stats.sets import SuiteStats
        stats_key_lifespan = 86400 # a day
        
        if not attrs:
            attrs = ['stories', 'followers']
        
        redis = RedisObject().get_redis_connection(slave=False)
        pipe = redis.pipeline()

        def recount(count_type):
            if count_type == "stories":
                return SuitePost.objects.all().filter(suite=self, post__status='published').count()            

            elif count_type == "followers":
                return Follow.objects.filter(content_type=ContentType.objects.get_for_model(Suite), object_id=self.pk, user__is_active=True).count()

        stats_from_key = SuiteStats(self.pk).get_all()
        response = {}
        to_recount = []

        for attr in attrs:
            try:
                response['%s' % attr] = stats_from_key[attr]
            except:
                to_recount.append(attr)
       
        if to_recount:
            for item in to_recount:
                count = recount(item)
                response['%s' % item] = count
                redis.pipeline(SuiteStats(self.pk).set(count, item))
            redis.pipeline(SuiteStats(self.pk).expire(stats_key_lifespan))
            pipe.execute

        return response

    def get_suite_editors(self):
        return SuiteMember.objects.filter(suite=self, status='editor')

    def get_suite_members(self):
        return SuiteMember.objects.all().filter(suite=self, user__is_active=True)

    def get_member_pks(self):
        return SuiteMember.objects.all().filter(suite=self, user__is_active=True).values_list('user__pk', flat=True)

    def get_featured_members(self, request):
        from suites.sets import SuiteFeaturedMembers
        
        featured_members = SuiteFeaturedMembers(self.pk).get_full_set()
        if not featured_members:
            redis = RedisObject().get_redis_connection(slave=False)
            pipe = redis.pipeline()

            featured_members = [self.owner.pk]   
            member_pks = self.get_member_pks()
            if member_pks:
                for mem in member_pks:
                    if self.is_editor(mem) and not mem in featured_members and len(featured_members) < 3:
                        featured_members.append(mem)

                # loop through again for non-eds (if necessary)
                if len(member_pks) > 1 and len(featured_members) < 3:
                    for mem in member_pks:
                        if not mem in featured_members and len(featured_members) < 3:
                            featured_members.append(mem)

            i = 0
            for m in featured_members:
                redis.pipeline(SuiteFeaturedMembers(self.pk).add_to_set(m,i))
                i += 1
            pipe.execute()

        if not featured_members:
            return None
        return get_serialized_list(request, featured_members, 'user:mini')

    def is_editor(self, member_pk):
        try:
            member = SuiteMember.objects.get(suite=self, user__pk=member_pk)
            return True if member.status == 'editor' or member.status == 'owner' else False
        except:
            return False

    def is_pending(self, user):
        requested = SuiteRequest.objects.filter(suite=self, status='pending', user=user)
        result = 'requested' if requested else None
        
        invited = SuiteInvite.objects.filter(suite=self, status='pending', user_invited=user)
        result = 'invited' if invited else None
        return result

    def get_users(self):                    
        members = SuiteMember.objects.filter(suite=self).values_list('user__pk')
        requested_users = SuiteRequest.objects.filter(suite=self, status='pending').values_list('user__pk')
        invited_users = SuiteInvite.objects.filter(suite=self, status='pending').values_list('user_invited__pk')
        return members, requested_users, invited_users

    def get_pending_data(self, request):
        num_invites = SuiteInvite.objects.all().filter(suite=self, status='pending').count()
        num_requests = SuiteRequest.objects.all().filter(suite=self, status='pending').count()
        return num_invites, num_requests

    def is_indexed(self):
        return True if self.owner.indexed else False

    def tweet_params_encoded(self):
        import urllib
        owner = '@%s' % self.owner.twitter_username if self.owner.twitter_username else self.owner.get_full_name()
        text = '"%s" by %s via @suiteio' % (self.name, owner)
        data = {
            'url': '%s%s' % (settings.SITE_URL, self.get_short_url()),
            'text': text.encode('utf-8', 'ignore')
        }
        return urllib.urlencode(data)

    def pin_params_encoded(self):
        import urllib
        if self.hero_image:
            image = self.hero_image.get_small_image_url()
        else:
            image = ''
        text = '%s' % self.description if self.description else ''
        data = {
            'url': '%s%s' % (settings.SITE_URL, self.get_short_url()),
            'media': image,
            'description': text.encode('utf-8', 'ignore')
        }
        return urllib.urlencode(data)

    def cleanup_images(self):
        """ delete all images that are no longer the hero """
        for image in self.images.all():
            if self.hero_image and not image == self.hero_image:
                image.delete()

    def get_suite_followers(self):
        from lib.models import Follow
        followers = Follow.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk, user__is_active=True)
        return [fol.user for fol in followers] if followers else []

    def get_follower_pks(self):
        from lib.models import Follow
        pks = Follow.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk, user__is_active=True).values_list('user_id', flat=True)
        if not pks:
            return []
        return pks

    def get_followers(self, request, page=None):
        # return paged results, has_next 
        follower_pks = self.get_follower_pks()
        has_next = False

        if page:
            page = int(page)
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE + 1
            if follower_pks:
                follower_pks = follower_pks[start:end]
                has_next = True if len(follower_pks) > DEFAULT_PAGE_SIZE else False

        if not follower_pks:
            return None, False

        json_objects = get_serialized_list(request, follower_pks, 'user:mini')
        return json_objects, has_next

    def invalidate(self):
        invalidate_object(self)   

    def delete(self):
        self.invalidate()
        return super(Suite, self).delete()


class SuitePost(TimeStampedModel):
    suite = models.ForeignKey(Suite, related_name='suite_posts')
    added_by = models.ForeignKey(AUTH_USER_MODEL, related_name='suite_posts_added', blank=True, null=True)
    message = models.TextField(max_length=140, blank=True, default='')

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    notification = GenericRelation(Notification)

    class Meta:
        ordering = ['-created']

    def invalidate(self):
        invalidate_object(self)   

    def fanout_notification(self):
        ''' fan out a notification to members, followers when someone joins '''
        
        fanout_list = []
        
        if self.suite.private:
            suite_members = self.suite.get_suite_members()
            for mem in suite_members:
                if not mem.user in fanout_list:
                    fanout_list.append(mem.user)

        else:
            suite_followers = list(self.suite.get_suite_followers())
            user_followers = list(self.added_by.get_follower_objects())
            suite_members = list([mem.user for mem in self.suite.get_suite_members()])


            for mem in suite_members + suite_followers + user_followers:
                if mem not in fanout_list:
                    fanout_list.append(mem)

        if not fanout_list:
            return
        new_notification(self, fanout_list)  


class SuiteStory(TimeStampedModel):
    suite = models.ForeignKey(Suite, related_name='suite_stories')
    story = models.ForeignKey('articles.Article', related_name='story_suites')
    added_by = models.ForeignKey(AUTH_USER_MODEL, related_name='suite_stories_added', blank=True, null=True)
    order = models.IntegerField(default=0, db_index=True)
    featured = models.BooleanField(default=False)
    message = models.TextField(max_length=140, blank=True, default='')
    notification = GenericRelation(Notification)  

    class Meta:
        ordering = ['-created']

    def invalidate(self):
        invalidate_object(self)   

    def fanout_notification(self):
        ''' fan out a notification to members, followers when someone joins '''
        
        fanout_list = []
        
        if self.suite.private:
            suite_members = self.suite.get_suite_members()
            for mem in suite_members:
                if not mem.user in fanout_list:
                    fanout_list.append(mem.user)

        else:
            suite_followers = list(self.suite.get_suite_followers())
            user_followers = list(self.added_by.get_follower_objects())
            suite_members = list([mem.user for mem in self.suite.get_suite_members()])


            for mem in suite_members + suite_followers + user_followers:
                if mem not in fanout_list:
                    fanout_list.append(mem)

        if not fanout_list:
            return
        new_notification(self, fanout_list)  

class SuiteMember(TimeStampedModel):
    suite = models.ForeignKey(Suite, related_name='members')
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='member_suites')
    STATUS = Choices('normal', 'editor', 'owner', 'blocked')
    status = models.CharField(choices=STATUS, default=STATUS.normal, max_length=20)
    notification_target = GenericRelation(Notification)  

    class Meta:
        ordering = ['created']
        unique_together = ('suite', 'user')

    class CacheKey:
        obj_cache_key = 'suite:member:obj'

    def invalidate(self):
        invalidate_object(self)   

    def fanout_notification(self):
        ''' fan out a notification to members, followers when someone joins '''
        
        fanout_list = [self.suite.owner]
        
        # in case editors are not following their own suite
        editors = self.suite.get_suite_editors()
        if editors:
            for ed in editors:
                if not ed in fanout_list:
                    fanout_list.append(ed)

        followers = self.owner.get_follower_objects()
        if followers:
            for fol in followers:
                if not fol in fanout_list:
                    fanout_list.append(fol)

        new_notification(self, fanout_list)        

def suite_images_file_name(instance, filename):
    import uuid
    return 'suite_images/orig/%s.jpg' % uuid.uuid4()

class SuiteImage(TimeStampedModel):
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='suite_images', null=True)

    image = models.ImageField(upload_to=suite_images_file_name)
    image_large = models.ImageField(upload_to='suite_images/large', blank=True, null=True)
    image_large_blur = models.ImageField(upload_to='suite_images/large_blur', blank=True, null=True)
    image_small = models.ImageField(upload_to='suite_images/small', blank=True, null=True)

    # TODO: remove this field once we've migrated current suites
    suite = models.ForeignKey(Suite, related_name='images', blank=True, null=True)

    top_position = models.IntegerField(default=0)
    left_position = models.IntegerField(default=0)
    scale = models.FloatField(default=1.0)

    caption = models.CharField(max_length=512, blank=True)
    credit = models.CharField(max_length=512, blank=True)
    credit_link = models.CharField(max_length=512, blank=True)

    def _image_url(self, image):
        if 'localhost' in settings.SITE_URL:
            # image = self.image
            # return "%s%s" % (settings.SITE_URL, image.url) if image else ''
            return ''
        else:
            return image.url if image else ''        

    def get_orig_image_url(self):
        return self._image_url(self.image)

    def get_large_image_url(self):
        return self._image_url(self.image_large)
        
    def get_large_blur_image_url(self):
        return self._image_url(self.image_large_blur)

    def get_small_image_url(self):
        return self._image_url(self.image_small)

    def invalidate(self):
        invalidate_object(self)
        
    def delete(self, *args, **kwargs):
        delete_all_images(self)
        super(SuiteImage, self).delete(*args, **kwargs)

class SuiteInvite(TimeStampedModel):
    """ An invitation from a suite editor to another user """
    suite = models.ForeignKey(Suite, related_name='invitations')
    user_inviting = models.ForeignKey(AUTH_USER_MODEL, related_name='invitations_sent')
    user_invited = models.ForeignKey(AUTH_USER_MODEL, related_name='invitations_received', blank=True, null=True)
    
    email_invite = models.BooleanField(default=False) 
    email = models.EmailField('invite email address', max_length=255, blank=True)

    message = models.TextField(blank=True)

    STATUS = Choices('pending', 'accepted', 'rejected')
    status = models.CharField(choices=STATUS, default=STATUS.pending, max_length=20)
    notification_target = GenericRelation(Notification)  
    
    class Meta:
        ordering = ['-created']
        unique_together = ('user_inviting', 'user_invited', 'suite', 'email')

    def delete(self, *args, **kwargs):
        super(SuiteInvite, self).delete(*args, **kwargs)

    def fanout_notification(self):
        ''' fan out a notification to the invited user '''
        fanout_list = []
        if not self.email_invite:
            fanout_list.append(self.user_invited)
        editors = self.suite.get_suite_editors()
        if editors:
            for ed in editors:
                if not ed in fanout_list:
                    fanout_list.append(ed)

        new_notification(self, fanout_list)     

class SuiteRequest(TimeStampedModel):
    """ A request to join a suite """
    suite = models.ForeignKey(Suite, related_name='suite_requests')
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='requested')

    message = models.TextField(blank=True)

    STATUS = Choices('pending', 'accepted', 'rejected')
    status = models.CharField(choices=STATUS, default=STATUS.pending, max_length=20)
    notification_target = GenericRelation(Notification)  

    class Meta:
        ordering = ['-created']
        unique_together = ('suite', 'user')

    def delete(self, *args, **kwargs):
        super(SuiteRequest, self).delete(*args, **kwargs)

    def fanout_notification(self):
        ''' fan out a notification to the suite's editors '''

        fanout_list = [self.suite.owner]
        editors = self.suite.get_suite_editors()
        if editors:
            for ed in editors:
                if not ed in fanout_list:
                    fanout_list.append(ed)

        new_notification(self, fanout_list) 

