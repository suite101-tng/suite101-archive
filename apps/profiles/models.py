import random, datetime, time, json, operator
from django.http import HttpRequest
from django.template.defaultfilters import timesince
from functools import reduce
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django.db import models
from django.db.models import Q, CharField, Value as V
from django.db.models.functions import Concat
from django.contrib.auth import get_user_model
from hashlib import sha1 as sha_constructor
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxLengthValidator
from django.core.cache import cache
from django.utils import timezone
from lib.enums import *
from notifications.models import Notification

from autoslug import AutoSlugField
from project import settings
from lib.cache import get_object_from_pk, invalidate_object
from lib.utils import api_serialize_resource_obj, get_serialized_list

class UserImage(models.Model):
    image = models.ImageField(upload_to='user_images/main')
    thumbnail = models.ImageField(upload_to='user_images/thumbs', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='profile_images', null=True, blank=True)

    def delete(self, *args, **kwargs):
        self.invalidate()
        super(UserImage, self).delete(*args, **kwargs)

    def invalidate(self):
        invalidate_object(self)

def user_background_file_name(instance, filename=None):
    import uuid
    return 'user_background/orig/%s.jpg' % uuid.uuid4()

class UserBackgroundImage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='background', null=True, blank=True)

    image = models.ImageField(upload_to=user_background_file_name)
    image_large = models.ImageField(upload_to='user_background/large', blank=True, null=True)
    image_small = models.ImageField(upload_to='user_background/small', blank=True, null=True)
    
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
        super(UserBackgroundImage, self).delete(*args, **kwargs)        

class SuiteUserManager(BaseUserManager):
    """
    Custom UserManager.
    Same as the regular django one, but we remove the username
    """
    def create_user(self, email=None, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email,
                          is_staff=False, is_active=False, is_superuser=False,
                          last_login=now, date_joined=now, **extra_fields)

        user.first_name = email.split('@')[0]
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)

        # create the email settings
        UserEmailSettings.objects.get_or_create(user=user)

        return user

    def create_superuser(self, email, password, **extra_fields):
        u = self.create_user(email, password, **extra_fields)
        u.first_name = email.split('@')[0]
        u.is_staff = True
        u.is_active = True
        u.activated = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


class SuiteUser(AbstractBaseUser, PermissionsMixin):
    """
    SuiteUser Model. Many fields taken from the core django AbstractUser
    But, we leave out username in favour of only logging in via email
    """
    DEFAULT_PROFILE_IMAGE = '%simages/temp_default_user.jpg' % settings.STATIC_URL
    email = models.EmailField('email address', max_length=255, unique=True, db_index=True)
    first_name = models.CharField('first name', max_length=50)
    last_name = models.CharField('last name', max_length=50)
    is_staff = models.BooleanField('staff status', default=False,
                                   help_text='Designates whether the user '
                                   'can log into this admin site.', db_index=True)
    is_active = models.BooleanField('active', default=False,
                                    help_text='Designates whether this user '
                                    'should be treated as active. Unselect this'
                                    ' instead of deleting accounts.')
    activated = models.BooleanField(default=False)
    is_moderator = models.BooleanField('moderator status', default=False,
                                   help_text='Designates whether the user '
                                   'can moderate content.')
    date_joined = models.DateTimeField('date joined', default=timezone.now)
    modified = models.DateTimeField('date modified', auto_now=True)

    slug = AutoSlugField(max_length=100, populate_from='get_full_name', unique=True, db_index=True, editable=True)
    by_line = models.CharField('Byline', max_length=200, blank=True, validators=[MaxLengthValidator(200)])
    full_bio = models.TextField(blank=True)
    location = models.CharField('Your home', max_length=64, blank=True)       
    profile_image = models.ForeignKey(UserImage, blank=True, null=True, on_delete=models.SET_NULL)
    user_background = models.ForeignKey('profiles.UserBackgroundImage', blank=True, null=True, related_name='user_background')

    tag_list = models.TextField(blank=True)

    # social, external accounts
    ga_code = models.CharField('Google Analytics tracking code', max_length=50, blank=True)
    twitter_username = models.CharField('Twitter Account', max_length=64, blank=True)
    facebook_url = models.URLField('Facebook Url', blank=True)
    facebook_username = models.CharField('Facebook Username', max_length=128, blank=True)
    personal_url = models.URLField('Your website', blank=True)
    googleplus_url = models.URLField('Google Plus Url', blank=True)
    twitter_connected = models.BooleanField(default=False)
    twitter_link_key = models.CharField(blank=True, max_length=40, default='')
    facebook_connected = models.BooleanField(default=False)

    # PRIVACY_NOBODY, PRIVACY_FOLLOWERS, PRIVACY_ANYBODY
    privacy = models.IntegerField(null=True, blank=True, default=PRIVACY_FOLLOWERS)

    # allow your email address to be exposed on your profile page
    show_email = models.BooleanField(default=False)

    # default advertising setting
    ads_enabled = models.BooleanField(default=True)

    accepted_terms = models.BooleanField(default=False)
    read_rules = models.BooleanField(default=False)

    # user's exposure is limited (usually as a sort of initial probation) if False
    approved = models.BooleanField(default=False, db_index=True)
    featured = models.DateTimeField(null=True, db_index=True)
    # disabled by red card!
    disabled = models.BooleanField(default=False)

    indexed = models.BooleanField(default=False, db_index=True)
    noindex_flag = models.BooleanField(default=False)

    # auth fields
    activation_key = models.CharField(blank=True, max_length=40, default='')
    reset_key = models.CharField(blank=True, max_length=40, default='')
    reset_time = models.DateTimeField(null=True, blank=True)

    # email changes
    new_email = models.EmailField(max_length=255, null=True, blank=True)
    email_key = models.CharField(blank=True, max_length=40, default='')
    email_change_time = models.DateTimeField(null=True, blank=True)

    last_known_ip = models.CharField(max_length=20, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_pub_date = models.DateTimeField(null=True, blank=True)
    
    # legacy info
    legacy_user_id = models.IntegerField(null=True, blank=True)

    # model manager and methods.
    objects = SuiteUserManager()

    followers = GenericRelation('lib.Follow')
    # suites = models.ManyToManyField('suites.Suite')

    notification_object = GenericRelation(Notification)            

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-date_joined']

    class CacheKey:
        obj_cache_key = 'user:obj'

    def __unicode__(self):
        return self.get_full_name()

    def get_absolute_url(self):
        if self.slug:
            try:
                return reverse('profile_detail', kwargs={'slug': self.slug})
            except:
                pass
        return ''

    @property
    def full_name(self):
        try:
            full_name = self.get_full_name()
        except:
            full_name = self.first_name
        return full_name

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        return '%s %s' % (self.first_name.strip(), self.last_name.strip())

    def get_short_name(self):
        return self.first_name.strip()

    def seen(self):
        return self.last_seen if self.last_seen else self.last_login

    def get_unread_notifs_count(self):
        from notifications.models import UserNotification
        return UserNotification.objects.filter(user=self, read=False).count()

    def get_my_notifications(self, request, notif_filter=None):
        from notifications.models import UserNotification
        
        try:
            if not notif_filter or notif_filter=='all':
                notif_pks = UserNotification.objects.filter(user=self).values_list('pk', flat=True)
            elif notif_filter=='msgs':
                    notif_pks = UserNotification.objects.filter(user=self, notification__chat_type=True).values_list('pk', flat=True)
            elif notif_filter=='mod' and request.user.is_moderator:
                notif_pks = UserNotification.objects.filter(user=self, notification__mod_type=True).values_list('pk', flat=True)
        except Exception as e:
            pass

        if not notif_pks:
            return None

        return get_serialized_list(request, notif_pks,'notif:mini')            

    def contactable(self, user):
        from profiles.sets import UserFollowsUsersSet
        if user.is_moderator:
            return True
        if self.privacy == 2:
            return True
        if not self.privacy:
            return False
        else:
            following = self.get_following_pks(follow_type='user:mini')
            return True if user.pk in following else False

    def needs_feed(self):
        from lib.models import Follow
        from articles.models import StoryParent
        following = Follow.objects.filter(user=self).count()
        if following:
            return True
        else:
            responses = StoryParent.objects.filter(content_object__author=self, story__status='published').count()
            if responses:
                return True
        return False

    def get_mod_notes(self):
        from moderation.models import ModNotes
        mod_notes = ModNotes.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk)
        if not mod_notes:
            return None
        return [note.serialize() for note in mod_notes]

    def sees_tour(self):
        from profiles.sets import UserSeesWelcomeTour
        return True if str(self.pk) in UserSeesWelcomeTour().get_full_set() else False

    def show_welcome_tour(self):
        from profiles.sets import UserSeesWelcomeTour
        UserSeesWelcomeTour().add_to_set(self.pk)

    def hide_welcome_tour(self):
        from profiles.sets import UserSeesWelcomeTour
        UserSeesWelcomeTour().remove_from_set(self.pk)

    def get_by_line(self):
        return self.by_line if self.by_line else ''

    def get_bio(self):
        return self.bio if self.bio else ''

    def get_location(self):
        return self.location if self.location else ''

    def get_profile_image(self):
        obj = self.profile_image
        if obj:
            return obj.image.url
        else:
            return self.DEFAULT_PROFILE_IMAGE

    def get_active_suite(self):
        from profiles.sets import UserActiveSuite
        return UserActiveSuite(self.pk).mget()[0]

    # def get_user_chats(self, page_num=None):
    #     from lib.sets import RedisObject
    #     from chat.models import Chat, ChatMember
    #     import time

    #     if page_num:
    #         page_num = int(page_num)
    #         start = (page_num - 1) * DEFAULT_PAGE_SIZE
    #         end = page_num * DEFAULT_PAGE_SIZE
    #         chat_pks = self.chats.distinct().values_list('chat__pk', flat=True).order_by('-chat__last_message_date')[start:end]
    #     else:
    #         chat_pks = self.chats.distinct().values_list('chat__pk', flat=True).order_by('-chat__last_message_date')
    #     return chat_pks

    # def get_unread_chats(self):
    #     from chat.sets import UserUnreadChatSet
    #     return UserUnreadChatSet(self.pk).get_full_set()

    def get_suite_invitations(self):
        return self.invitations_received.all()

    def member_of(self, suite):
        if suite.owner == self:
            return True
        try:
            self.member_suites.get(suite=suite)
        except:
            return False
        return True

    def invited_to(self, suite):
        try:
            suite.invitations.get(user_invited=self, status='pending')
            return True
        except:
            return False

    def get_my_suites(self, request, show_all=False):
        from lib.utils import get_serialized_list
        page = int(request.GET.get('page', '1'))
        page = None if show_all else page

        to_render = query = split_querystring = None

        if page:
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE
        else:
            start = 0
            end = -1

        querystring = str(request.GET.get('q', ''))

        if querystring:
            split_querystring = querystring.split('-')
            query = reduce(operator.and_, (Q(suite__name__icontains=x) for x in split_querystring))

        if not request.user.is_authenticated():
            if query:
                suite_pks = self.member_suites.filter(query).filter(suite__private=False).values_list('suite__pk', flat=True).order_by('-suite__modified')
            else:
                suite_pks = self.member_suites.filter(suite__private=False).values_list('suite__pk', flat=True).order_by('-suite__modified')
        else:
            if query:
                member_objects = self.member_suites.filter(query).order_by('-suite__modified')
            else:
                member_objects = self.member_suites.all().order_by('-suite__modified')

            viewer_member_suites = request.user.member_suites.all().values_list('suite__pk', flat=True)
            suite_pks = []
            for obj in member_objects:
                if obj.suite.private:
                    try:
                        if obj.suite.pk in viewer_member_suites and obj.suite.pk not in suite_pks:
                            suite_pks.append(obj.suite.pk)
                    except Exception as e:
                        continue

                elif obj.suite.pk not in suite_pks:
                    suite_pks.append(obj.suite.pk) 

        if not suite_pks:
            return None

        try:
            suite_objs = get_serialized_list(request, suite_pks[start:end],'suite:mini')
        except Exception as e:
            suite_objs = None
            print('problem getting list of suites: %s' % e)

        return suite_objs
        # return get_serialized_list(request, suite_pks[start:end],'suite:mini')

    @property
    def current(self):
        return self.is_current_user()

    def is_current_user(self):
        import time
        from lib.enums import CURRENT_RANGE

        try:
            current_threshold = datetime.datetime.now() - datetime.timedelta(days=int(CURRENT_RANGE))
        except:
            return False
        return True if self.last_pub_date > current_threshold else False

    def reset_last_published_date(self):
        from articles.models import Article
        try:
            stories = Article.objects.published().filter(author=self).order_by('-created')        
            if stories:
                self.last_pub_date = stories[0].created
                self.invalidate()
                self.save()
        except Exception as e:
            print(e)

    def expire_stats_key(self, key):
        from stats.sets import UserStats
        UserStats(self.pk).delete(key)

    @property
    def followers_count(self):
        return self.get_followers_count()

    def get_followers_count(self):
        return int(self.get_user_stats(['followers'])['followers'])

    def get_stories_count(self):
        return int(self.get_user_stats(['stories'])['stories'])

    # Get a dictionary with core user stats
    def get_user_stats(self, attrs=[]):
        from lib.models import Follow
        from suites.models import Suite
        from lib.sets import RedisObject
        from stats.sets import UserStats
        stats_key_lifespan = 86400 # a day
        User = get_user_model()
        if not attrs:
            attrs = ['stories', 'drafts', 'suites', 'followers', 'folsuites', 'folusers']
        
        redis = RedisObject().get_redis_connection(slave=False)
        pipe = redis.pipeline()

        def recount(count_type):
            if count_type == "stories":
                from articles.models import Article
                return Article.objects.published().filter(author=self).count()

            elif count_type == "drafts":
                from articles.models import Article
                return Article.objects.drafts().filter(author=self).count()

            elif count_type == "suites":
                return self.member_suites.all().count()

            elif count_type == "folsuites":
                return Follow.objects.filter(content_type=ContentType.objects.get_for_model(Suite), user=self).count()

            elif count_type == "folusers":
                fol = Follow.objects.filter(content_type=ContentType.objects.get_for_model(User), user=self).count()
                return Follow.objects.filter(content_type=ContentType.objects.get_for_model(User), user=self).count()

            elif count_type == "followers":
                return Follow.objects.filter(content_type=ContentType.objects.get_for_model(User), object_id=self.pk, user__is_active=True).count()

        try:
            stats_from_key = json.dumps(UserStats(self.pk).get_all())
        except:
            stats_from_key = []


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
                response['%s' % item] = int(count)
                redis.pipeline(UserStats(self.pk).set(count, item))
            redis.pipeline(UserStats(self.pk).expire(stats_key_lifespan))
            pipe.execute

        return response

    def get_user_stories(self, request, page=None, hide_user=False):
        from lib.utils import get_serialized_list
        from articles.models import Article
        objects = None

        page_num = int(request.GET.get('page', '1'))
        query = str(request.GET.get('q', ''))
        named_filter = str(request.GET.get('filter', ''))

        # # override feed_type
        # feed_type = request.GET.get('feedtype', None)

        start = (page_num - 1) * DEFAULT_PAGE_SIZE  
        end = page_num * DEFAULT_PAGE_SIZE + 1
        has_previous = True if page_num > 1 else False
        has_next = False

        if query:
            split_querystring = query.split('-')
            query = reduce(operator.and_, (Q(title__icontains=x) for x in split_querystring))

            if named_filter and named_filter=="draft" and self == request.user:
                pks = self.articles.drafts().filter(query).values_list('pk', flat=True)[start:end]            
            else:
                pks = self.articles.published().filter(query).values_list('pk', flat=True)[start:end]     

        else:
            if named_filter and named_filter=="draft" and self == request.user:
                pks = self.articles.drafts().values_list('pk', flat=True)[start:end]            
            else:
                pks = self.articles.published().values_list('pk', flat=True)[start:end]     


        if pks: 
            has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
            objects = get_serialized_list(request, pks,'story:mini')[:DEFAULT_PAGE_SIZE]

        if not objects:
            return None
        return objects

    def get_mutual_follows(self):
        from profiles.sets import MutualFollowsSet
        return MutualFollowsSet(self.pk).get_full_set()

    def is_following(self, obj_pk, follow_type):
        if not obj_pk:
            return False
        try:
            return obj_pk in self.get_following_pks(follow_type)
        except:
            return False

    def get_follower_objects(self):
        from lib.models import Follow
        followers = Follow.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk, disabled=False, user__is_active=True)
        return [fol.user for fol in followers] if followers else None

    def get_follower_pks(self):
        from lib.models import Follow
        pks = Follow.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk, disabled=False).values_list('user_id', flat=True)
        if not pks:
            return None
        return pks

    def get_followers(self, request, page=None):
        # return paged results, has_next 
        follower_pks = self.get_follower_pks()
        if not follower_pks:
            return None, False
        count = len(follower_pks)
        if page:
            page = int(page)
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE + 1
            follower_pks = follower_pks[start:end]
            has_next = True if len(follower_pks) > DEFAULT_PAGE_SIZE else False

        if not follower_pks:
            return None, False

        json_objects = get_serialized_list(request, follower_pks[:DEFAULT_PAGE_SIZE], 'user:mini')
        if not json_objects:
            return None, False
        return json_objects, has_next

    def get_followers_count(self):
        fols = self.get_follower_pks()
        return len(fols) if fols else 0

    def get_following(self, request, follow_type='user', page=None):
        # pass user or suite follow_type
        
        from lib.models import Follow
        from lib.utils import get_serialized_list
        page = int(request.GET.get('page', '1'))
        # page = None if show_all else page

        to_render = query = split_querystring = None

        if page:
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE + 1
        else:
            start = 0
            end = -1

        querystring = str(request.GET.get('q', ''))
        if querystring:
            pks = self.get_following_pks(follow_type)
            split_querystring = querystring.split('-')
            if follow_type == 'user':
                User = get_user_model()
                query = reduce(operator.and_, (Q(full_name__icontains=x, pk__in=list(pks)) for x in split_querystring))
                pks = User.objects.annotate(full_name=Concat('first_name', V(' '), 'last_name')).filter(is_active=True).filter(query).values_list('pk', flat=True)[start:end]
            elif follow_type == 'suite':
                query = reduce(operator.and_, (Q(name__icontains=x, pk__in=list(pks)) for x in split_querystring))
                pks = Suite.objects.filter(owner__is_active=True).filter(query).values_list('pk', flat=True)[start:end]                

        else:
            pks = self.get_following_pks(follow_type, page)

        if not pks:
            return None, False

        has_next = True if len(pks) > DEFAULT_PAGE_SIZE else False
        follow_key = follow_type + ":mini"
        json_objects = get_serialized_list(request, pks[:DEFAULT_PAGE_SIZE], follow_key)
        if not json_objects:
            return None, False
        return json_objects, has_next


    def get_following_pks(self, follow_type='user', page=None):
        from lib.models import Follow
        from suites.models import Suite
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection(slave=True)
        pipe = redis.pipeline()
        following_pks = []
        cache_key = 'user:fols:%s:%s' % (follow_type, self.pk)

        if page:
            start = (page - 1) * DEFAULT_PAGE_SIZE
            end = page * DEFAULT_PAGE_SIZE + 1
        else:
            start = 0
            end = -1

        following_pks = redis.zrevrange(cache_key, start, end)
        if not following_pks and not page > 1:
            following_pks = []
            redis = RedisObject().get_redis_connection(slave=False)

            if follow_type == 'user':
                pks = Follow.objects.filter(user=self) \
                    .filter(content_type=ContentType.objects.get_for_model(self)) \
                    .filter(disabled=False) \
                    .values_list('object_id', 'created')

            if follow_type == 'suite':
                pks = Follow.objects.filter(user=self) \
                    .filter(content_type=ContentType.objects.get_for_model(Suite)) \
                    .filter(disabled=False) \
                    .values_list('object_id', 'created')

            if pks:
                for pk, created in pks:
                    created = time.mktime(created.timetuple())
                    if not len(following_pks) > DEFAULT_PAGE_SIZE:
                        following_pks.append(pk)
                    pipe.zadd(cache_key, pk, created)
                pipe.expire(cache_key, settings.DEFAULT_CACHE_TIMEOUT)
                pipe.execute()

            if not following_pks:
                return []
        return following_pks


    def tweet_params_encoded(self):
        from urllib.parse import urlencode
        text = '"%s" via @suiteio' % self.get_full_name()
        data = {
            'url': '%s%s' % (settings.SITE_URL, self.get_absolute_url()),
            'text': text.encode('utf-8', 'ignore')
        }
        return urlencode(data)

    def _create_key(self):
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        email = self.email
        if isinstance(email, unicode):
            email = email.encode('utf-8')
        return sha_constructor(salt + email).hexdigest()

    def create_activation_key(self):
        ''' create an activation key for this new user based on their email as a salt '''
        self.activation_key = self._create_key()
        self.save()

    def create_reset_key(self):
        ''' create an reset key for this new user based on their email as a salt '''
        self.reset_key = self._create_key()
        self.reset_time = datetime.datetime.now()
        self.save()

    def activate_user(self):
        ''' we've successfully authenticated the email and activation key, we can set our user flag to active '''
        self.activation_key = ''
        self.is_active = True
        self.activated = True
        self.save()

    def set_new_email(self, email):
        self.email_key = self._create_key()
        self.email_change_time = datetime.datetime.now()
        self.new_email = email
        self.save()

    def complete_email_change(self):
        self.email = self.new_email
        self.new_email = ''
        self.email_key = ''
        self.email_change_time = None
        self.save()

    def invalidate(self):
        invalidate_object(self)

    def mark_deleted(self):
        """ delete the user, but not really """
        from articles.models import Article
        self.invalidate()
        self.is_active = False
        self.save()

        for article in self.articles.all():
            article.status = Article.STATUS.deleted
            article.save()

        # return super(SuiteUser, self).delete()

class UserEmailSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='email_settings')
    daily_summary = models.BooleanField(default=True)
    new_posts = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=True)
    all_chat_messages = models.BooleanField(default=True)
    notifications = models.BooleanField(default=True)
    product_updates = models.BooleanField(default=True)


class UserBlackList(models.Model):
    email = models.EmailField()
    last_known_ip = models.CharField(max_length=20, blank=True)
