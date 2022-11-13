import celery
import logging
import boto
import time
import datetime

from PIL import Image
from io import StringIO

from django.core.mail import get_connection, EmailMultiAlternatives
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from django.template import loader, Context
from django.utils import translation
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage

from static_sitemaps import conf
from static_sitemaps.generator import SitemapGenerator
from lib.utils import blur_image
from lib.enums import *
from articles.templatetags.bleach_filter import bleach_filter

logger = logging.getLogger(__name__)

@celery.task(name='lib.tasks.resize_image')
def resize_image(genericImage):
    from lib.utils import resize_generic_image
    resize_generic_image(genericImage)
    
@celery.task(name='lib.tasks.refresh_sitemaps')
def refresh_sitemaps(force=False):
    from lib.utils import task_ready
    import subprocess
    from stats.sets import AdminTaskMonitor, RunTask
    
    ''' Schedule this task to run every 15 minutes or so -- if needed, we regenerate sitemaps, 
        rsync them to the app servers, ping Google '''
    today = datetime.date.today()
    if task_ready('sitemaps') or force:
        try:
            generator = SitemapGenerator(verbosity=1)
            generator.write()

            # rsync sitemaps to app servers
            subprocess.call(['rsync', '-avz', '/home/suite/sitemaps/', 'suite@10.179.100.36:/home/suite/sitemaps/'])
            subprocess.call(['rsync', '-avz', '/home/suite/sitemaps/', 'suite@10.69.160.117:/home/suite/sitemaps/'])

            # task is complete (until next publish, etc)           
            task_ready('sitemaps', 'done')

        except Exception as e:
            print(e)
            # message = EmailMessage(
            #     'Daily sitemaps refresh FAILED',
            #     'Best take a look!',
            #     'dev@suite.io',
            #     ['michael@suite.io']
            # )
            # message.send()
            pass

@celery.task(name='lib.tasks.process_unfollow')
def process_unfollow(unfollowed_object, user):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    from profiles.tasks import remove_mutual_follow
    from articles.models import Article
    from suites.models import Suite, SuitePost
    from lib.sets import RedisObject
    from articles.sets import UserMainStoryFeed
    User = get_user_model()

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()

    unfollowed_object.expire_stats_key('followers')
    content_type = ContentType.objects.get_for_model(unfollowed_object)
    if content_type == ContentType.objects.get_for_model(Suite):
        user.expire_stats_key('folsuites')
        suite_post_objects = SuitePost.objects.all().filter(suite=unfollowed_object, content_type=ContentType.objects.get_for_model(Article), post__status='published')
        if suite_post_objects:
            for obj in suite_post_objects:
                post = obj.content_object
                if not user.is_following(post.author.pk, 'user'):
                    redis.pipeline(UserMainStoryFeed(user.pk).remove_from_set(post.pk))                  

    elif content_type == ContentType.objects.get_for_model(User):
        user.expire_stats_key('folusers')
        remove_mutual_follow(user, unfollowed_object)
        story_pks = Article.objects.published().filter(author=unfollowed_object).values_list('pk', flat=True)
        if story_pks:
            for pk in story_pks:
                redis.pipeline(UserMainStoryFeed(user.pk).remove_from_set(pk))                  
    
    unfollowed_object.save() # to rebuild elasticsearch object
    pipe.execute()

@celery.task(name='lib.tasks.process_new_follow')
def process_new_follow(follow):
    import time, datetime
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    from articles.models import Article
    from suites.models import Suite, SuitePost
    from lib.sets import RedisObject
    from articles.sets import UserMainStoryFeed

    from profiles.tasks import process_mutual_follow
    User = get_user_model()

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()

    try:
        follow.fanout_notification()
    except Exception as e:
        print(e)

    followed_object = follow.content_object
    user = follow.user
    content_type = follow.content_type

    followed_object.expire_stats_key('followers')

    if content_type == ContentType.objects.get_for_model(Suite):
        user.expire_stats_key('folsuites')
        suite_post_objects = SuitePost.objects.all().filter(suite=followed_object, content_type=ContentType.objects.get_for_model(Article), post__status='published')
        if suite_post_objects:
            for obj in suite_post_objects:
                post = obj.content_object
                time_score = time.mktime(post.created.timetuple())
                redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(post.pk, time_score))                  

    elif content_type == ContentType.objects.get_for_model(User):
        user.expire_stats_key('folusers')
        stories = Article.objects.published().filter(author=followed_object)
        if stories:
            for story in stories:
                time_score = time.mktime(story.created.timetuple())
                redis.pipeline(UserMainStoryFeed(user.pk).add_to_set(story.pk, time_score))                  
        try:
            process_mutual_follow(followed_object, user)
            send_email_alert.delay(followed_object, followed_object, user)
        except Exception as e:
            print(e)

    followed_object.save() # to rebuild elasticsearch object    

    pipe.execute()

@celery.task(name='lib.tasks.user_index_check')
def user_index_check(user):
    from lib.enums import INDEX_STORY_COUNT_THRESHOLD
    from articles.models import Article
    from django.db.models import Avg
    stories = user.get_stories_count()

    # Refresh user index status
    if user.approved:
        if stories >= INDEX_STORY_COUNT_THRESHOLD and not user.noindex_flag:
            user.indexed = True
        else:
            user.indexed = False
    else:
        user.indexed = False

    user.save()
    user.invalidate()  


@celery.task(name='lib.tasks.send_email')
def send_email(emails, subject, template_name, email_context, bcc=None):
    from project import settings as proj_settings

    # mark emails for staging and localhost
    if 'staging' in proj_settings.SITE_URL:
        subject = '(STAGING) %s' % subject
    elif 'localhost' in proj_settings.SITE_URL:
        subject = '(LOCALHOST) %s' % subject

    message_text = loader.get_template('%s.txt' % template_name).render(email_context)
    message_html = loader.get_template('%s.html' % template_name).render(email_context)

    # # FOR TESTING ONLY!!!!!!!!
    emails = ['team@suite.io', ]

    
    from_email = proj_settings.FROM_EMAIL
    connection = get_connection(username=proj_settings.EMAIL_HOST_USER,
                    password=proj_settings.EMAIL_HOST_PASSWORD,
                    fail_silently=True)
    # send emails out.
    for to_email in emails:
        if not to_email or to_email == '':
            continue

        mail = EmailMultiAlternatives(subject, message_text, from_email, [to_email],
                                      connection=connection)
        mail.attach_alternative(message_html, 'text/html')
        mail.send()


@celery.task(name='lib.tasks.send_email_alert')
def send_email_alert(user, obj, other_user=None, extra_object=None):
    from project import settings as proj_settings
    from suites.models import SuiteRequest, SuiteInvite
    from articles.models import ArticleRecommend, Article
    from moderation.models import RoyalApplication
    from lib.models import Follow

    # import pdb; pdb.set_trace()
    if isinstance(obj, SuiteRequest):
        email_title = '%s has asked to join your Suite' % other_user.get_full_name()
        email_template = 'emails/suiterequest'
    elif isinstance(obj, SuiteInvite):
        email_title = '%s has invited you to join a Suite' % other_user.get_full_name()
        email_template = 'emails/suiteinvite'
    elif isinstance(obj, Article):
        title = obj.title if obj.title else "Untitled"
        email_title = '%s responded to %s' % (other_user.get_full_name(), title)
        email_template = 'emails/response'
    elif isinstance(obj, RoyalApplication):
        email_title = 'You\'ve been accepted into Suite\'s royalties program'
        email_template = 'emails/royal_accepted'
    elif isinstance(obj, Follow):
        if obj.content_type.model == 'suiteuser':
            email_title = '%s is now following you' % other_user.get_full_name()
        else:
            email_title = '%s is now following your Suite' % other_user.get_full_name()
        email_template = 'emails/follow'

    if email_title and user.email_settings.notifications:
        send_email(
            [user.email, ],
            email_title,
            email_template,
            {
                'site_url': proj_settings.SITE_URL,
                'user': user,
                'other_user': other_user,
                'obj': obj,
                'extra_object': extra_object,
            }
        )

@celery.task(name='lib.tasks.send_external_invite')
def send_external_invite(obj, email_address=None, sender=None):   
    from project import settings as proj_settings 
    from suites.models import SuiteInvite

    if isinstance(obj, SuiteInvite):
        sender = obj.user_inviting
        email_address = obj.email
        email_subject = '%s has invited you to collaborate on %s' % (sender.get_full_name(), obj.suite.name)
        email_template = 'emails/suiteinvite_external'

    # elif isinstance(obj, Converstaion) and sender and email_address: # sender and email_address are required
    #     email_subject = '%s has added you to a discussion on Suite' % (initiator.get_full_name())
    #     email_template = 'emails/conv_invite_external'

    if email_address and email_subject and email_template:
        send_email(
            [email_address],
            email_subject,
            email_template,
            {
                'site_url': proj_settings.SITE_URL,
                'sender': sender,
                'obj': obj
            }
        )

@celery.task(name='lib.tasks.new_member')
def new_member(user):
    # ensure the user sees the welcome tour (set key)
    user.show_welcome_tour()

@celery.task(name='lib.tasks.resize_suite_hero_image')
def resize_suite_hero_image(image_pk):
    import urllib
    import httplib

    from suites.models import SuiteImage
    from project import settings as proj_settings
    from lib.utils import check_rotation

    try:
        image_object = SuiteImage.objects.get(pk=image_pk)
    except:
        return

    if proj_settings.DEBUG or 'staging' in proj_settings.SITE_URL:
        image = Image.open(StringIO(image_object.image.read()))
    else:
        try:
            if not 'http' in image_object.image.url:
                image_url = 'http:%s' % image_object.image.url
            else:
                image_url = image_object.image.url
            img_file = urllib.urlopen(image_url)
            image = Image.open(StringIO(img_file.read()))
        except httplib.IncompleteRead:
            return

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

    img_width = image.size[0]
    img_height = image.size[1]

    # first thing we do is determine if the image is too big - we limit the width for filesize
    if img_width > HERO_IMAGE_LARGE_WIDTH:
        # figure out the new height.
        new_height = img_height * HERO_IMAGE_LARGE_WIDTH / img_width
        large_image = image.resize((HERO_IMAGE_LARGE_WIDTH, new_height), Image.ANTIALIAS)
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

    # save a blurred version
    large_image_blur = blur_image(large_image)
    temp_file = NamedTemporaryFile(delete=True)
    large_image_blur.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.image_large_blur.save(filename, File(temp_file))

    # save the small version to file
    if image_object.image_small:
        image_object.image_small.delete()

    new_height = img_height * HERO_IMAGE_SMALL_WIDTH / img_width
    image_small = image.resize((HERO_IMAGE_SMALL_WIDTH, new_height), Image.ANTIALIAS)

    temp_file = NamedTemporaryFile(delete=True)
    image_small.save(temp_file, format="JPEG", quality=JPEG_IMAGE_QUALITY)
    image_object.image_small.save(filename, File(temp_file))

    image_object.save()

    # there's a race condition where this image_object may not have had a suite
    # when this method was called, but by the end of it, there is a suite.
    # so we grab the object again.. just to see if we can catch it.
    image_object = SuiteImage.objects.get(pk=image_object.pk)
    # this might be uploaded before the suite is saved.
    if image_object.suite:
        image_object.suite.invalidate()
    image_object.invalidate()

    return True, image_object.image.url

@celery.task(name='lib.tasks.invalidate_user_slugs')
def invalidate_user_slugs(user):
    from lib.sets import RedisObject
    from profiles.sets import UserTeaser
    from articles.sets import StoryTeaser
    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()  

    try:
        user.invalidate()
        redis.pipeline(UserTeaser(user.pk).clear())
        for story in user.articles.all():
            story.invalidate()
            redis.pipeline(StoryTeaser(story.pk).clear())
            children = story.get_response_pks()
            if children:
                for child_pk in children:
                    redis.pipeline(StoryTeaser(child_pk).clear())
    except Exception as e:
        print(e)
    pipe.execute()

@celery.task(name='lib.tasks.send_weekly_digest')
def send_weekly_digest():
    from lib.utils import email_weekly_digest
    for user in User.objects.filter(is_active=True).filter(email_settings__weekly_digest=True):
        email_weekly_digest(user, user)
