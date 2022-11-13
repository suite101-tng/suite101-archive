from django.db import models
import json
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model

from django.conf import settings
from model_utils import Choices
from model_utils.models import TimeStampedModel
from django.core.urlresolvers import reverse

from notifications.models import Notification, UserNotification

# use AUTH_USER_MODEL here to prevent circular import
from project.settings import AUTH_USER_MODEL
from lib.utils import delete_all_images, generate_hashed_id, get_serialized_list, diff
from lib.enums import *

class Follow(TimeStampedModel):
    # thing being followed, using a generic foreign key
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # user doing the following
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='users_following')
    disabled = models.BooleanField(default=False)
    notification_object = GenericRelation(Notification)

    class Meta:
        ordering = ['-created']

    def fanout_notification(self):
        from suites.models import Suite
        ''' fan out a notification for this story '''
        from notifications.utils import new_notification
        User = get_user_model()

        ''' fan out follows to the following person's followers and 
            (if user) the followed person, or (if suite) the members 
            of the followed suite '''

        fanout_list = []
        # testing
        fanout_list = [User.objects.get(pk=7444)]

        followers = self.user.get_follower_objects()
        if followers:
            for follower in followers:
                if not follower in fanout_list:
                    fanout_list.append(follower)

        if self.content_type == ContentType.objects.get_for_model(Suite):
            suite_members = self.get_suite_members()
            if suite_members:
                for member in suite_members:
                    if not member in fanout_list:
                        fanout_list.append(member)

        elif self.content_type == ContentType.objects.get_for_model(User):
            if not self.content_object == self.user and not self.content_object in fanout_list:
                fanout_list.append(self.content_object)

        new_notification(self, fanout_list)

def generic_images_file_name(instance, filename=None):
    import uuid
    return 'images/orig/%s.jpg' % uuid.uuid4()

class GenericImage(models.Model):
    image = models.ImageField(upload_to=generic_images_file_name, blank=True, null=True)
    image_large = models.ImageField(upload_to='images/large', blank=True, null=True)
    image_small = models.ImageField(upload_to='images/small', blank=True, null=True)
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='images')

    upload_url = models.URLField(null=True, blank=True)

    caption = models.CharField(max_length=512, blank=True) # can be overriden by embed object
    credit = models.CharField(max_length=512, blank=True)
    credit_link = models.CharField(max_length=512, blank=True)

    def save(self, *args, **kwargs):
        if self.upload_url and not self.image:
            from django.core.files.base import ContentFile
            from lib.utils import download_image_from_url, valid_img
            import cStringIO
            image = download_image_from_url(self.upload_url)
            if image:
                try:
                    filename = generic_images_file_name(self)
                    self.image = filename
                    tempfile = image
                    tempfile_io = cStringIO.StringIO() # Will make a file-like object in memory that you can then save
                    tempfile.save(tempfile_io, format=image.format)
                    self.image.save(filename, ContentFile(tempfile_io.getvalue()), save=False) # Set save=False otherwise you will have a looping save method
                    self.upload_url = ''
                except Exception as e:
                    print ("Error trying to save model: saving image failed: " + str(e))
                    pass
        super(GenericImage, self).save(*args, **kwargs) 

    def get_orig_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image.url) if self.image else ''
        else:
            return self.image.url if self.image else ''

    def get_large_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image_large.url) if self.image_large else ''
        else:
            return self.image_large.url if self.image_large else ''

    def get_small_image_url(self):
        if 'localhost' in settings.SITE_URL:
            return "%s%s" % (settings.SITE_URL, self.image_small.url) if self.image_small else ''
        else:
            return self.image_small.url if self.image_small else ''

    def invalidate(self):
        invalidate_object(self)  

    def delete(self, *args, **kwargs):
        delete_all_images(self)
        super(GenericImage, self).delete(*args, **kwargs)