import time, json
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from lib.utils import get_mod_users
from notifications.models import Notification
from notifications.utils import new_notification
from model_utils.models import TimeStampedModel
from model_utils import Choices
from lib.enums import *

# use AUTH_USER_MODEL here to prevent circular import
from project.settings import AUTH_USER_MODEL

class FlagManager(models.Manager):
    def active(self):
        return super(FlagManager, self).all().filter(cleared=False)

class ModTags(TimeStampedModel):
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='mod_tags')
    tag_list = models.TextField(blank=True)

class ModNotes(TimeStampedModel):
    ''' Moderator notes about a user or other entity '''
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    moderator = models.ForeignKey(AUTH_USER_MODEL, related_name='notes')
    message = models.TextField()
    notification_object = GenericRelation(Notification)    

    class Meta:
        ordering = ['-created']

    def serialize(self):
        data = {}
        data['msg'] = self.message
        data['created'] = time.mktime(self.created.timetuple())
        data['moderator'] = {}
        data['moderator']['fullName'] = self.moderator.get_full_name()
        data['moderator']['firstName'] = self.moderator.first_name
        data['moderator']['mainImageUrl'] = self.moderator.get_profile_image()
        data['moderator']['absoluteUrl'] = self.moderator.get_absolute_url()
        return data

    def fanout_notification(self, notif_type=None):
        ''' fan out a notification to mods '''

        fanout_list = get_mod_users()
        new_notification(self, fanout_list, mod_type=True)  

class Flag(TimeStampedModel):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    reason = models.CharField(max_length=100)
    message = models.TextField(blank=True)

    cleared = models.BooleanField(default=False)
    objects = FlagManager()

    # user going the flagging
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='flagged')

    class Meta:
        ordering = ['-created']

class RoyalApplication(TimeStampedModel):
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='royal_applications')
    STATUS = Choices('pending', 'accepted', 'rejected')
    status = models.CharField(choices=STATUS, default=STATUS.pending, max_length=20)
    message = models.CharField(max_length=1000, blank=True)
    editor_note = models.CharField(max_length=1000, blank=True) # akin to a congrats or rejection slipmodels
    editor = models.ForeignKey(AUTH_USER_MODEL, null=True, related_name='editor') # author of the editor_note, person who made the decision

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return self.user.get_full_name()

    @property
    def accepted(self):
        return self.status == self.STATUS.accepted

    @property
    def rejected(self):
        return self.status == self.STATUS.rejected





