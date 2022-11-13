from django.db import models
import json, datetime
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from lib.cache import invalidate_object

from django.conf import settings
from model_utils import Choices
from model_utils.models import TimeStampedModel
from django.core.urlresolvers import reverse
from project.settings import AUTH_USER_MODEL
from lib.enums import *

class Notification(models.Model):
    '''Generic notifications model'''

    date = models.DateTimeField(null=True, db_index=True)
   
    # We will frequently filter these types, so let's make it easier
    mod_type = models.BooleanField(default=False, db_index=True) 
    chat_type = models.BooleanField(default=False, db_index=True) 

    # the main content object
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-date']

    def create(self, *args, **kwargs):
        if not self.date:
            self.date = datetime.datetime.now() 
        return super(Notification, self).create(*args, **kwargs)        

    def delete(self, *args, **kwargs):
        self.invalidate()
        return super(Notification, self).delete(*args, **kwargs)        

    def invalidate(self):
        invalidate_object(self)

    def is_referenced(self):
        user_notifs = UserNotification.objects.filter(notification=self)
        return True if user_notifs else False


class UserNotification(TimeStampedModel):
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='notifications', db_index=True)
    notification = models.ForeignKey('notifications.Notification', blank=True, null=True, related_name='notification')
    # Read/unread
    read = models.BooleanField(default=False)    

    class Meta:
        ordering = ['-notification__date']
        unique_together = ('user', 'notification')

    def delete(self, *args, **kwargs):
        self.invalidate()
        return super(UserNotification, self).delete(*args, **kwargs)

    def invalidate(self):
        ''' invalidate obj, api resources '''
        invalidate_object(self)        

@receiver(post_delete, sender=UserNotification)
def notifs_housekeeping(sender, instance, using, **kwargs):
    try:
        if not instance.notification.is_referenced():
            instance.notification.delete()
    except:
        pass
