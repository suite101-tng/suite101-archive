import json
import time, datetime
# import struct
import gc
# import base64
import base32_crockford
import uuid
from dateutil import parser
from PIL import Image, ImageFilter
from io import StringIO
from django.http import HttpRequest, Http404

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from lib.enums import *
# from zbase32 import *
from project import settings

def resize_generic_image(image_object, read_S3=False):
    from PIL import Image
    from io import StringIO
    from django.core.files import File
    from django.core.files.temp import NamedTemporaryFile
    from lib.utils import check_rotation
    from lib.enums import GENERIC_IMAGE_LARGE_WIDTH, GENERIC_IMAGE_MAX_SMALL_WIDTH, JPEG_IMAGE_QUALITY

    # open up the original image
    if read_S3:
        import urllib
        import httplib
        try:
            img_file = urllib.urlopen(image_object.image.url)
            image = Image.open(StringIO(img_file.read()))
        except httplib.IncompleteRead:
            return
    else:
        image = Image.open(StringIO(image_object.image.read()))

    try:
        exif_data = image._getexif()
    except:
        exif_data = None

    # make sure to convert to RGB before we process
    try:
        image = image.convert("RGB")
    except:
        # if this fails, it is because something is wrong with the image and we
        # should not proceed any further.
        return

    # check for iOS rotation
    image = check_rotation(image, exif_data)

    filename = image_object.image.name

    # first thing we do is determine if the image is too large.
    if image_object.image.width > GENERIC_IMAGE_LARGE_WIDTH:
        # if it's too wide, we size the image down.
        new_height = image_object.image.height * GENERIC_IMAGE_LARGE_WIDTH / image_object.image.width
        large_image = image.resize((GENERIC_IMAGE_LARGE_WIDTH, new_height), Image.ANTIALIAS)
    else:
        large_image = image

    # save the large version to file
    try:
        image_object.image_large.delete()
    except:
        pass
    temp_file = NamedTemporaryFile(delete=True)
    large_image.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.image_large.save(filename, File(temp_file))

    # save the small version to file
    try:
        image_object.image_small.delete()
    except:
        pass

    new_height = image_object.image.height * GENERIC_IMAGE_MAX_SMALL_WIDTH / image_object.image.width
    image_small = large_image.resize((GENERIC_IMAGE_MAX_SMALL_WIDTH, new_height), Image.ANTIALIAS)
    temp_file = NamedTemporaryFile(delete=True)
    image_small.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.image_small.save(filename, File(temp_file))
    return

def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

def get_mod_users():
    User = get_user_model()
    return User.objects.filter(is_moderator=True, is_active=True)

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

def percentage(value):  
    try:  
        return round((value * 100),1)
    except ValueError:  
        return '' 

def diff(a, b):
    b = set(b)
    return [aa for aa in a if aa not in b]

def rgb_to_hex(rgb_triplet):
    import webcolors
    try:
        normalized_triplet = webcolors.normalize_integer_triplet(rgb_triplet)
        hex_value = webcolors.rgb_to_hex(normalized_triplet)
    except:
        # fall back on defaul color
        hex_value = DEFAULT_HEX_COLOR
    return hex_value

def hex_to_rgb(hexadecimal):
    import webcolors
    if not hexadecimal[0]=="#":
        hexadecimal = '#' + hexadecimal
    try:
        normalized_hex = webcolors.normalize_hex(hexadecimal)
    except:
        # fall back on defaul color
        normalized_hex = webcolors.normalize_hex(DEFAULT_HEX_COLOR)
    rgb_triplet = webcolors.hex_to_rgb(normalized_hex)
    return rgb_triplet

def get_serialized_list(request, pk_list, content_type):
    from lib.cache import get_object_from_pk
    from articles.models import Article
    from conversations.models import Conversation, Post
    from suites.models import Suite, SuitePost
    from links.models import Link
    from notifications.models import UserNotification
    from moderation.models import Flag
    
    from conversations.api import ConversationResource, PostResource, PostMiniResource
    from notifications.api import UserNotificationResource
    from articles.api import StoryMiniResource
    from profiles.api import UserMiniResource
    from suites.api import SuiteMiniResource, SuitePostResource
    from links.api import LinkMiniResource
    from moderation.api import FlagResource
    from support.models import SupportQuestion
    from support.api import SupportQuestionResource
    from lib.sets import RedisObject   

    User = get_user_model()
    keys = []
    redis = RedisObject().get_redis_connection(slave=True)
    pipe = redis.pipeline()
    if pk_list:
       
        for pk in pk_list:
            keys.append('%s:%s' % (content_type,str(pk)))
        consolidated_teaser_list = redis.mget(keys)

        json_objs = []
        loc = 0
        if consolidated_teaser_list:
            # get the teasers
            for teaser in consolidated_teaser_list:
                # if we didn't fetch json for this pk, we build some now
                if teaser:
                    json_objs.append(json.loads(teaser.decode('utf-8')))
                else:
                    missing_pk = pk_list[loc]
                    if content_type == 'user:mini':
                        model = User
                        resource = UserMiniResource()
                    elif content_type == 'story:mini':
                        model = Article
                        resource = StoryMiniResource()    
                    elif content_type == 'conv:mini':
                        model = Conversation
                        resource = ConversationResource()                                                   
                    elif content_type == 'post':
                        model = Post
                        resource = PostResource()   
                    elif content_type == 'post:mini':
                        model = Post
                        resource = PostMiniResource()
                    elif content_type == 'suite:mini':
                        model = Suite
                        resource = SuiteMiniResource()  
                    elif content_type == 'link:mini':
                        model = Link
                        resource = LinkMiniResource()                             
                    elif content_type == 'notif:mini':
                        model = UserNotification
                        resource = UserNotificationResource()  
                    elif content_type == 'flag:mini':
                        model = Flag
                        resource = FlagResource()    
                    elif content_type == 'support:mini':
                        model = SupportQuestion
                        resource = SupportQuestionResource()                            
                    try:
                        obj = get_object_from_pk(model, missing_pk, False)
                        if obj:
                            fresh_json = api_serialize_resource_obj(obj, resource, request)
                            if fresh_json:
                                json_objs.append(fresh_json)
                    except Exception as e:
                        print('get_serialized_list failed to get type %s: %s' % (content_type, e))
                        pass                                                     
                loc += 1 # keep correct teaser_list location


            try:
                if request.user and request.user.is_authenticated():
                    if content_type == 'story:mini':
                        for obj in json_objs:
                            obj['ownerViewing'] = request.user.pk == int(obj['author']['id']) or request.user.is_moderator
                            obj['isMod'] = True if request.user.is_moderator else False
                    # if content_type == 'conversation':
                    #     from conversation.utils import unread_in_conversation
                    #     for obj in json_objs:
                    #         unread = unread_in_conversation(obj['id'], request.user.pk)
                    #         if unread:
                    #             obj['newMessages'] = int(unread)

                    if content_type == 'user:mini' or content_type == 'suite:mini':    
                        for obj in json_objs:
                            try:
                                obj['viewerFollowing'] = request.user.is_following(obj['id'], content_type)
                            except Exception as e:
                                pass
            except:
                pass

        return json_objs

def api_serialize_resource_obj(obj, resource, request):
    from lib.sets import RedisObject
    import json    
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()
    do_cache = True

    if not obj:
        return None
    json_str = None
    try:
        do_cache = False if request.user and request.user.is_authenticated() and not resource._meta.cache_authed else True
    except:
        pass

    data_cache_key = resource._meta.data_cache_key    
    if data_cache_key and do_cache:
        data_cache_key = data_cache_key + ':%s' % obj.pk    
        try:
            json_str = redis.get(data_cache_key).decode('utf-8')
        except: 
            pass

    if not json_str:
        bundle = resource.build_bundle(obj=obj, request=request)
        json_str = resource.serialize(request, resource.full_dehydrate(bundle), 'application/json')
        if data_cache_key and do_cache:
            pipe.set(data_cache_key, json_str)
            pipe.expire(data_cache_key, settings.DEFAULT_CACHE_TIMEOUT)
            pipe.execute()
        if not json_str:
            return None

    return json.loads(json_str)

def api_serialize_resource_list(resource, request):
    request_bundle = resource.build_bundle(request=request)
    queryset = resource.obj_get_list(request_bundle)[:20]

    bundles = []
    for obj in queryset:
        bundle = resource.build_bundle(obj=obj, request=request)
        bundles.append(resource.full_dehydrate(bundle, for_list=True))

    bundles_json_str = resource.serialize(None, bundles, "application/json")
    return json.loads(bundles_json_str.decode('utf-8')), bundles_json_str

def get_discussed_stories(page=None):
    from articles.sets import DiscussedStoriesSet
    def fetch_pks():
        if page:
            return DiscussedStoriesSet().get_set(page)
        else: 
            return DiscussedStoriesSet().get_full_set()

    pks = fetch_pks()
    if page and not page > 1 and not pks:
        from django.db import models
        from articles.models import Article, StoryParent
        from lib.sets import RedisObject
        redis = RedisObject().get_redis_connection()
        pipe = redis.pipeline()

        stories_with_responses = StoryParent.objects.filter(story__status='published', content_type=ContentType.objects.get_for_model(Article)).values('object_id').annotate(responses=models.Count('story__pk'))
        for story_tuple in stories_with_responses:
            redis.pipeline(DiscussedStoriesSet().add_to_set(story_tuple['object_id'], story_tuple['responses']))
        pipe.execute()
        pks = fetch_pks()
        if not pks:
            return None
    return pks

def get_top_stories(time_period=7, page=None):
    from lib.sets import RedisObject
    from articles.sets import GlobalMostReadStories
    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()

    if not time_period:
        time_period = 7

    def fetch_pks():
        if page:
            return GlobalMostReadStories(time_period).get_set(page)
        else: 
            return GlobalMostReadStories(time_period).get_full_set()

    def fetch_date_range():
        start = datetime.datetime.now() - datetime.timedelta(days=int(time_period))
        end = datetime.datetime.now()
        date_range = []
        for d in daterange(start, end):
            date = d.strftime("%Y-%m-%d")
            date_range.append(date)
        return date_range

    def add_to_sets(loop):
        fetch = pipe.execute()     
        if fetch:  
            for f in fetch:
                story_pk = story_pks[loop]
                reads_in_period = int(round(sum([float(i or 0) for i in f]),0))
                redis.pipeline(GlobalMostReadStories(time_period).add_to_set(story_pk, reads_in_period))
                loop += 1
            pipe.execute()
        return loop

    pks = fetch_pks()
    if not pks and not page > 1:
        from articles.models import Article
        suite_epoch = parser.parse(SUITE_EPOCH)
        date_range = fetch_date_range()

        loop_threshold = 200 # number of requests we'll add to the pipeline at a time
        length_limit = 200 # keep extremely short posts out of top lists
        story_pks = Article.objects.published().filter(author__approved=True, author__is_active=True, created__gte=suite_epoch, word_count__gte=length_limit).values_list('pk', flat=True)
        loop = 0 # story index
        inner_loop = 0 # reset with each add_to_sets
        for story_pk in story_pks:         
            pipe.hmget('s:d:story:reads:%s' % story_pk, date_range) # reads
            if not inner_loop < loop_threshold:
                loop = add_to_sets(loop)
                inner_loop = 0
            inner_loop +=1   

        if inner_loop:
            # and for that last loop...
            add_to_sets(loop)
        pks = fetch_pks()

    if not pks:
        raise Http404
    return pks

def get_top_tags(page=None, filter_type='read'):
    from lib.sets import RedisObject, TopTags
    from articles.models import Article

    tags = None
    # tag_cache_lifespan = settings.DEFAULT_CACHE_TIMEOUT
    tag_cache_lifespan = 3600 # refresh every hour

    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    def fetch_tags():
        if page:
            return TopTags(filter_type).get_set(page)
        else: 
            return TopTags(filter_type).get_full_set()

    def recache_story_tags(stories):
        i = 0
        for story in stories:
            tags_loaded = json.loads(str(story.tag_list))
            for tag in tags_loaded:
                redis.pipeline(TopTags(filter_type).increment(tag, 1))
                i += 1
            if i > 500:
                i = 0
                pipe.execute()
        redis.pipeline(TopTags(filter_type).expire(tag_cache_lifespan))
        pipe.execute()

    def get_top_discussed_tags():     
        # most frequently seen tags from out most discussed stories
        tags = fetch_tags()
        if not tags:
            discussed_stories = get_discussed_stories()
            stories_with_tags = Article.objects.published().filter(author__approved=True, pk__in=list(discussed_stories)).exclude(tag_list='' or [])
            if stories_with_tags:
                recache_story_tags(stories_with_tags)
            tags = fetch_tags()
        if not tags:
            return None
        return tags

    def get_featured_tags():  
        # moderator-featured tags
        tags = fetch_tags()
        if not tags:
            top_stories = get_top_stories(time_period=7)
            stories_with_tags = Article.objects.published().filter(author__approved=True, pk__in=list(top_stories)).exclude(tag_list='' or [])
            if stories_with_tags:
                recache_story_tags(stories_with_tags)
            tags = fetch_tags()
        if not tags:
            return None
        return ['feminism', 'motherhood', 'physics']

    def get_top_read_tags():  
        # most frequently seen tags from out most discussed stories
        try:
            tags = fetch_tags()
            if not tags:
                top_stories = get_top_stories(time_period=7)
                stories_with_tags = Article.objects.published().filter(author__approved=True, pk__in=list(top_stories)).exclude(tag_list='' or [])
                if stories_with_tags:
                    recache_story_tags(stories_with_tags)
                tags = fetch_tags()
            if not tags:
                return None
            return tags
        except Exception as e:
            return None

    def get_top_written_about_tags():
        print('getting top written-about tags')

    if filter_type == "read":
        tags = get_top_read_tags()  
    elif filter_type == "discussed":
        tags = get_top_discussed_tags()                      
    # elif filter_type == "written":
    #     tags = get_top_written_tags()
    elif filter_type == "featured":
        tags = get_featured_tags()            

    if not tags:
        return None
    return tags

def get_featured_suites():
    from suites.sets import FeaturedSuiteSet
    from suites.models import Suite
    from lib.sets import RedisObject

    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    pks = FeaturedSuiteSet().get_full_set()
    if pks:
        return pks
    else:
        greats = Suite.objects.filter(featured__isnull=False).exclude(private=True).values_list('pk', flat=True).order_by('-featured')
        if greats:
            for g_pk in greats:
                redis.pipeline(FeaturedSuiteSet().add_to_set(g_pk))
            pipe.execute()
            return greats
    return None

def get_featured_members():
    from profiles.sets import FeaturedMemberSet
    from lib.sets import RedisObject
    User = get_user_model()
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    pks = FeaturedMemberSet().get_full_set()
    if pks:
        return pks
    else:
        greats = User.objects.filter(featured__isnull=False).values_list('pk', flat=True).order_by('-featured')
        if greats:
            for g_pk in greats:
                redis.pipeline(FeaturedMemberSet().add_to_set(g_pk))
            pipe.execute()
            return greats
    return None

def get_recommended_stories():
    from articles.sets import RecommendedStoriesSet
    from lib.sets import RedisObject
    from articles.models import Article
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    pks = RecommendedStoriesSet().get_full_set()
    if not pks:
        pks = []
        featured = Article.objects.published().filter(featured__isnull=False, author__is_active=True).order_by('-featured')
        if featured:
            for story in featured:
                date = int(time.mktime(story.created.timetuple()))
                redis.pipeline(RecommendedStoriesSet().add_to_set(story.pk))
                pks.append(story.pk)
            pipe.execute()
    if pks:
        return pks
    return None

def get_lead_story():
    from random import randint, randrange
    from articles.sets import LeadStoryPool
    from articles.utils import has_large_main_image
    from lib.sets import RedisObject

    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()

    lead_pool = LeadStoryPool().get_full_set()   
    if not lead_pool:
        lead_pool = []
        recommended = get_recommended_stories()
        if recommended:
            for story_pk in recommended:
                add = has_large_main_image(story_pk)
                if add:
                    redis.pipeline(LeadStoryPool().add_to_set(story_pk))
                    lead_pool.append(story_pk)
            pipe.execute()               
        
    if lead_pool:
        upper = len(lead_pool)
        randkey = randint(0,upper-1)                    
        return lead_pool[randkey]
    return None

def seems_like_email(email):
    """Checks for a syntactically valid email address."""

    domains = "aero", "asia", "biz", "cat", "com", "coop", \
        "edu", "gov", "info", "int", "jobs", "mil", "mobi", "museum", \
        "name", "net", "org", "pro", "tel", "travel"

    # Email address must be 7 characters in total.
    if len(email) < 7:
        return False # Address too short.

    # Split up email address into parts.
    try:
        localpart, domainname = email.rsplit('@', 1)
        host, toplevel = domainname.rsplit('.', 1)
    except ValueError:
        return False # Address does not have enough parts.

    # Check for Country code or Generic Domain.
    if len(toplevel) != 2 and toplevel not in domains:
        return False # Not a domain name.

    for i in '-_.%+.':
        localpart = localpart.replace(i, "")
    for i in '-_.':
        host = host.replace(i, "")

    if localpart.isalnum() and host.isalnum():
        return True # Email address is fine.
    else:
        return False # Email address has funny characters.

def datetime_to_epoch(dt):
    import time
    time_ = time.mktime(dt.timetuple())
    return time_

def epoch_to_datetime(time_):
    return datetime.datetime.fromtimestamp(time_)

def get_named_url_patterns():
    """ modified version of http://djangosnippets.org/snippets/1434/ """
    """ we're only interested in the top level urls, so we return strings
        just before the first / """
    from django.core import urlresolvers

    resolver = urlresolvers.get_resolver(None)
    patterns = sorted([
        value[0][0][0].split('/')[0]
        for key, value in resolver.reverse_dict.items()
        if isinstance(key, basestring)
    ])
    return patterns

def get_slug_status(slug, user=None):
    swear_words = ['fuck','fucker','fuckhead','fuckface','fucking','fucked','shit','merde','ass','asshole','cunt']
    url_patterns = get_named_url_patterns()
    error = None

    if slug in swear_words:
        error = 'swear'
    elif slug in url_patterns:
        error = 'taken'
    else:
        try:
            if user:
                if slug==user.slug:
                    error = 'isyou'   
                else:
                    get_user_model().objects.exclude(pk=user.pk).get(slug=slug)
                    error = 'taken'
            else:
                get_user_model().objects.get(slug=slug)
                error = 'taken'                    
        except:
            pass
    
    return {'error': error }


def check_unique_top_level_url(slug, exclude_pk=None):
    url_patterns = get_named_url_patterns()
    if slug in url_patterns:
        return False
    try:
        if exclude_pk:
            get_user_model().objects.exclude(pk=exclude_pk).get(slug=slug)
        else:
            get_user_model().objects.get(slug=slug)
    except:
        return True
    else:
        return False


def set_unique_top_level_url(slug, exclude_pk=None):
    temp_url = slug
    counter = 1

    while not check_unique_top_level_url(temp_url, exclude_pk):
        temp_url = "%s-%d" % (slug, counter)
        counter += 1

    return temp_url


def check_suite_slug(owner, slug, exclude_pk=None):
    from suites.models import Suite
    try:
        if exclude_pk:
            Suite.objects.exclude(pk=exclude_pk).get(owner=owner, slug=slug)
        else:
            Suite.objects.get(owner=owner, slug=slug)
    except:
        return True
    else:
        return False


def set_unique_suite_url(owner, slug, exclude_pk=None):
    temp_url = slug
    counter = 1

    while not check_suite_slug(owner, temp_url):
        temp_url = "%s-%d" % (slug, counter)
        counter += 1

    return temp_url


def send_activation_email(user, twitter=False, facebook=False, next=None):
    from lib.tasks import send_email
    emails = [user.email, ]
    user.create_activation_key()
    activation_url = reverse('profile_activate', kwargs={
        'pk': user.pk,
        'activation_key': user.activation_key
    })
    full_url = '%s%s' % (settings.SITE_URL, activation_url)
    if next:
        full_url = '%s?next=%s' % (full_url, next)
    context = {
        'user': user,
        'activation_url': full_url,
        'twitter': twitter,
        'facebook': facebook
    }
    send_email.delay(emails, 'Welcome to Suite!', 'emails/activate', context)


def send_welcome_email(user):
    User = get_user_model()
    from django.utils.html import strip_tags
    from django.template.loader import render_to_string
    from lib.tasks import send_email
    from project import settings as proj_settings

    # create a message that will go into their inbox, and create a notification.
    message = render_to_string('emails/_welcome_message.html', {'user': user})

    # send out the welcome email from michael
    emails = [user.email, ]
    context = {
        'user': user,
        'michael': michael,
        'site_url': proj_settings.SITE_URL,
    }
    send_email.delay(emails, 'Welcome to Suite', 'emails/welcome', context)

def send_flag_email(url, reason, message, user):
    from lib.tasks import send_email
    # emails = ['hello@suite.io', ]
    emails = ['team@suite.io', ]
    context = {
        'user_name': user.get_full_name(),
        'user_email': user.email,
        'message': message,
        'reason': reason,
        'url': '%s%s' % (settings.SITE_URL, url)
    }
    send_email.delay(emails, 'Flag Report', 'emails/flag', context)


def send_reset_email(request, user):
    from lib.tasks import send_email
    emails = [user.email, ]
    reset_url = None
    
    try:
        reset_url = reverse('pw_reset_with_key', kwargs={
            'reset_key': user.reset_key
        })
        print('reset url? %s' % reset_url)
    except Exception as e:
        print('failed to get reset url: %s' % e)

    context = {
        'user': user,
        'reset_url': '%s%s' % (settings.SITE_URL, reset_url),
    }
    send_email(emails, 'Reset your password', 'emails/reset', context)


def send_email_change_email(request, user):
    from lib.tasks import send_email
    emails = [user.new_email, ]
    email_url = reverse('profile_change_email', kwargs={
        'pk': user.pk,
        'email_key': user.email_key
    })

    context = {
        'user': user,
        'email_url': '%s%s' % (settings.SITE_URL, email_url),
    }
    send_email.delay(emails, 'Change your email', 'emails/change_email', context)


def send_request_rejection_email(join_request):
    from lib.tasks import send_email
    emails = [join_request.user.email, ]
    context = {
        'user': join_request.user,
        'message': join_request.message,
        'suite': join_request.suite
    }
    send_email.delay(emails, 'You asked to join %s' % join_request.suite.name, 'emails/suite_rejection', context)


def send_twitter_error_email(request, exception_e):
    from lib.tasks import send_email
    emails = ['michael@suite.io', ]
    context = {
        'request_get': "%s" % request.GET,
        'exception_e': exception_e,
    }
    send_email.delay(emails, 'Twitter Error', 'emails/twitter_error', context)


def queryset_iterator(queryset, chunksize=1000):
    '''''
    http://djangosnippets.org/snippets/1949/
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()

def valid_img(img):
    import imghdr
    # Check if valid instance of PIL Image class
    type = img.format
    if type in ('GIF', 'JPEG', 'JPG', 'PNG', 'ICO'):
        try:
            img.verify()
            return True
        except:
            return False
    else: return False 

def download_image_from_url(url):
    import urllib2, requests
    from urllib.parse import urlparse
    import cStringIO
    from PIL import Image, IcoImagePlugin
    import copy
    from bisect import insort_left

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
        r = urllib2.Request(url, headers=headers)
        raw = requests.get(url)
        img = Image.open(StringIO(raw.content))


        # request = urllib2.urlopen(r, timeout=10)
        # image_data = cStringIO.StringIO(request.read()) # StringIO imitates a file, needed for verification step
        # img = Image.open(image_data) # Creates an instance of PIL Image class - PIL does the verification of file
        img_copy = copy.copy(img) 

        if not valid_img(img_copy):
            return None

        if img_copy.format and img_copy.format == 'ICO':
            try:
                # see what sizes are in the (tuple) ico file
                ico_sizes = img.ico.sizes()
                # now order the sizes(w) so we can get the largest    
                ordered_sizes = []    
                for i in ico_sizes:
                    insort_left(ordered_sizes,i[0])

                target_size = ordered_sizes[-1]
                ico_image = img.ico.getimage(target_size)
                return ico_image

            except Exception as e:
                print('--- did not get an image from the ICO file: %s' % e)

    except Exception as e:
        print('failed to fetch an image file: %s' % e)
    if valid_img(img_copy):
        return img
    else:
        # Maybe this is not the best error handling...you might want to just provide a path to a generic image instead
        return None

def delete_all_images(image):
    # delete all other images!
    image.invalidate()
    try:
        image.image.delete()
    except:
        pass
    try:
        image.image_large.delete()
    except:
        pass
    try:
        image.image_small.delete()
    except:
        pass

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return strip_non_ascii(ip)


def resize_profile_image(image_object):
    """ resize the image object and return the the url of the main image """
    # open up the original image
    image = Image.open(StringIO(image_object.image.read()))
    try:
        exif_data = image._getexif()
    except:
        exif_data = None

    filename = '%s.jpg' % uuid.uuid4()

    # make sure to convert to RGB before we process
    try:
        image = image.convert("RGB")
    except:
        # if this fails, it is because something is wrong with the image and we
        # should not proceed any further.
        return False, ''

    # check for iOS rotation
    image = check_rotation(image, exif_data)

    max_width = PROFILE_IMAGE_MAX_WIDTH
    max_thumb_width = PROFILE_IMAGE_MAX_THUMB_WIDTH

    # save the original image, but with lower quality so we're not
    # loading super huge images all the time
    if image_object.image.width > max_width:
        # if the image is too wide, restrict it's size
        new_height = int(float(max_width) * float(image_object.image.height) / float(image_object.image.width))
        image = image.resize((max_width, new_height), Image.ANTIALIAS)

    image_object.image.delete()
    temp_file = NamedTemporaryFile(delete=True)
    image.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.image.save(filename, File(temp_file))

    if image_object.thumbnail:
        image_object.thumbnail.delete()
    new_height = int(float(max_thumb_width) * float(image_object.image.height) / float(image_object.image.width))
    thumbnail = image.resize((max_thumb_width, new_height), Image.ANTIALIAS)
    temp_file = NamedTemporaryFile(delete=True)
    thumbnail.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.thumbnail.save(filename, File(temp_file))

    return True, image_object.image.url

ORIENTATION = 274
ORIENTATION_ROTATE_90 = 6
ORIENTATION_ROTATE_270 = 8

def check_rotation(image, exif_data=None):
    """ assume an ALREADY opened image object here """
    if not exif_data:
        return image

    # check to see if this was an iOS image and if rotation is needed
    if ORIENTATION in exif_data.keys():
        orientation = exif_data[ORIENTATION]
        if orientation == ORIENTATION_ROTATE_90:
            image = image.rotate(-90)
        elif orientation == ORIENTATION_ROTATE_270:
            image = image.rotate(-270)

    # this doesn't save the image.. just returns it!
    return image

def blur_image(image_object, radius=HERO_IMAGE_BLUR_RADIUS):
    class MyGaussianBlur(ImageFilter.Filter):
        """ 
        thanks wellfire interactive!
        http://www.wellfireinteractive.com/blog/python-image-enhancements/ 
        """
        name = "GaussianBlur"
        def __init__(self, radius=2):
            self.radius = radius
        def filter(self, image):
            return image.gaussian_blur(self.radius)

    return image_object.filter(MyGaussianBlur(radius=radius))
    
def suite_render(request, template_name, context, multiple=False):
    from django.template import RequestContext
    # import pdb; pdb.set_trace()
    try:
        if multiple:
            return node_render_multiple(template_name, context)
        else:
            return node_render(template_name, context)
    except Exception as e:
        print('failed to render with node: (template: %s) - %s' % (template_name, e))
        return Http404()

def _node_render(url_base, template_name, context):
    import urllib.request
    import urllib.error
    from urllib.parse import urlencode

    url_params = {
        'templateName': template_name,
        'context': json.dumps(context)
    }

    # data = urllib.parse.urlencode(d).encode("utf-8")
    # req = urllib.request.Request(url)
    # with urllib.request.urlopen(req,data=data) as f:
    #     resp = f.read()
    #     print(resp)
            
    req = urllib.request.Request(url_base, urlencode(url_params).encode("utf-8"))
    response = urllib.request.urlopen(req)
    return response.read()


def node_render(template_name, context):
    try:
        url = '%s%s' % (settings.NODE_PRIMARY_URL, '/single')
        return _node_render(url, template_name, context)
    except:
        url = '%s%s' % (settings.NODE_SECONDARY_URL, '/single')
        return _node_render(url, template_name, context)


def node_render_multiple(template_name, context):
    try:
        url = '%s%s' % (settings.NODE_PRIMARY_URL, '/multiple')
        return _node_render(url, template_name, context)
    except:
        url = '%s%s' % (settings.NODE_SECONDARY_URL, '/multiple')
        return _node_render(url, template_name, context)


def check_user_ip_ban(request):
    from profiles.models import UserBlackList
    ip_address = get_client_ip(request)
    blacklist = UserBlackList.objects.filter(last_known_ip=ip_address)
    if blacklist.count() >= 2:
        return True
    return False


def generate_hashed_id(user_id, object_type, object_id):
# | xxxx...xxx | xxxxx       | xxxxxxxxxx  | <- 64bits
# | object_id  | object_type | user_id(mod)|
    new_id = user_id % (2 ** 10)
    new_id = new_id | object_type << 10
    new_id = new_id | object_id << 15
    return encode_id(new_id)

def decode_hashed_id(hashed_id_str):
    try:
        hashed_id = int(decode_id(str(hashed_id_str)))
        object_id = hashed_id >> 15
        object_type = (hashed_id & 0x7C00) >> 10
    except Exception as e:
        log_failed_decodes(hashed_id,e or '')
    # mod'd user_id here is not really useful to us unless we start to shard the DBs...
    # user_id = hashed_id & 0x3FF
    return object_type, object_id

def log_failed_decodes(hashed_id,exception):
    from profiles.sets import FailedDecodesSet
    try:
        FailedDecodesSet().set(exception,hashed_id)
    except Exception as e:
        print(e)

def encode_id(to_encode):
    '''
    encode and strip the leading y's
    take the number, pack it into a character string, and encode that string
    then strip all leading y's since y represents zero
    '''
    # z-base32
    # return b2a(struct.pack('>q', to_encode)).lstrip('y')
    # base32 crockford
    return base32_crockford.encode(to_encode).lower()

def task_ready(task_name, status=None):
    from stats.sets import RunTask
    if task_name and not status:
        return True if int(RunTask().get('sitemaps')) else False
    elif task_name and status=='done':
        RunTask().set(0,task_name)
    else:
        RunTask().set(status,task_name)

def decode_id(to_decode):
    '''
    decode and add leading y's
    '''
    # return struct.unpack('>q', a2b(str(to_decode).rjust(13, 'y')))[0]
    return base32_crockford.decode(to_decode.upper())

def replace_relative_links(html_text):
    """ replace relative (internal) links to absolute ones """
    return html_text.replace('href="/', 'href="%s/' % settings.SITE_URL) \
                    .replace('src="//', 'src="https://') \
                    .replace('url(//', 'url(https://')


def email_weekly_digest(user, send_to, delay=False):
    """ for each active user, we want to send them a weekly email
        that will summarize their week and hopefully bring them back
        if they haven't been on the site in a while """
    from django.http import HttpRequest
    from articles.models import Article
    from articles.utils import render_teasers
    from lib.tasks import send_email

    last_week = datetime.datetime.now() - datetime.timedelta(days=7)

    email_context = {}
    email_context['user'] = user
    email_context['total_reads'] = int(user.stats.total_reads)

    # we'll add loves here later.

    # responses in the last week
    responses = Article.objects.filter(parent__author=user).filter(created__gte=last_week)
    responses_rendered = render_teasers(HttpRequest(), responses, show_user=True, template='story-email-teaser')
    email_context['responses_rendered'] = replace_relative_links(responses_rendered)

    # now we find some articles the user may have missed, for that we look at their feed.
    missed_stories = []
    for story in UserStoryFeed(user.pk).get_feed():
        # we don't want to show stories by the user, or responses to the user here.
        if story.author == user:
            continue
        # if story.parent and story.parent.author == user:
        #     continue
        missed_stories.append(story)
        if len(missed_stories) == 3:
            break

    missed_stories_rendered = render_teasers(HttpRequest(), missed_stories, show_user=True, template='story-email-teaser')
    email_context['missed_stories'] = replace_relative_links(missed_stories_rendered)

    emails = [send_to.email, ]
    # don't use delay here since we're already being called from a task.
    if delay:
        send_email.delay(emails, 'Suite Weekly Digest', 'emails/weekly_digest', email_context)
    else:
        send_email(emails, 'Suite Weekly Digest', 'emails/weekly_digest', email_context)

def rebuild_user_feed(user):
    '''rebuild the user's main story feed'''
    from articles.models import Article, StoryParent
    from suites.models import Suite, SuitePost
    from lib.sets import RedisObject
    from articles.sets import UserMainStoryFeed
    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()  

    countem = 0

    # TODO: responses to you
    # TODO: stories you've added to your Suites

    following_users = user.get_following_pks('user')                
    following_suites = user.get_following_pks('suite')

    if following_users:
        print('------ adding followed users')
        for folpk in following_users:
            stories = Article.objects.published().filter(author__is_active=True, author__pk=folpk).iterator()
            if stories:
                for story in stories:
                    countem +=1
                    try:
                        time_score = time.mktime(story.created.timetuple())
                    except Exception as e:
                        print('no time_score: %s' % e)
                    redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(story.pk, time_score)) 

        pipe.execute()

    if following_suites:
        for folpk in following_suites:
            suite_posts = SuitePost.objects.filter(suite__pk=folpk, content_type=ContentType.objects.get_for_model(Article), post__author__is_active=True, post__status="published")
            if suite_posts:
                for post_object in suite_posts:
                    countem +=1
                    time_score = time.mktime(post_object.content_object.created.timetuple())
                    redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(post_object.object_id, time_score)) 
        pipe.execute()

    your_stories = Article.objects.published().filter(author=user).iterator()
    if your_stories:
        for story in your_stories:
            countem +=1
            time_score = time.mktime(story.created.timetuple())
            redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(story.pk, time_score)) 
        pipe.execute()

    return countem
