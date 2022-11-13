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

from .models import UserNotification
from lib.enums import *
from articles.templatetags.bleach_filter import bleach_filter

logger = logging.getLogger(__name__)

@celery.task(name='lib.notifications.fanout_notification')
def fanout_notification(notification, fanout_list):
    insert_list = []
    exists = UserNotification.objects.filter(user__in=list(fanout_list), notification=notification).values_list('user__pk', flat=True)
    for fanny in fanout_list:
        if not fanny.pk in exists:
            insert_list.append(UserNotification(notification=notification, user=fanny))
    if insert_list:
        try:
            UserNotification.objects.bulk_create(insert_list)        
        except Exception as e:
            print('problem doing bulk user notifs insert (fanout): %s' % e)
            logger.error(e)
            for fanny in fanout_list:
                if not fanny.pk in exists:
                    try:
                        notif, created = Notification.objects.get_or_create(content_type=content_type,object_id=content_object.pk)
                        notif.date = date
                        notif.save()
                    except Exception as e:
                        print('problem doing backup notifcation create: %s' % e)
                        logger.error(e)
                        pass

@celery.task(name='lib.notifications.clear_unread_notifications')
def clear_unread_notifications(user, content_object=None):
    from django.contrib.contenttypes.models import ContentType
    from suites.models import SuiteRequest, SuiteInvite
    from notifications.models import UserNotification
    
    persistent_types = [ContentType.objects.get_for_model(model) for model in [SuiteRequest, SuiteInvite]]

    if content_object:
        try:
            if str(content_object.content_type) == str(ContentType.objects.get_for_model(Chat)):
                UserNotification.objects.filter(user=user, notification__content_object=content_object).delete()
            else:
                UserNotification.objects.filter(user=user, notification__content_object=content_object).update(read=True)
        except Exception as e:
            print('problem deleting chat notif: %s' % e)
        
    else:
        try:
            UserNotification.objects.filter(user=user).exclude(notification__chat_type=False, notification__mod_type=False, notification__content_type__in=list(persistent_types)).update(read=True)
        except Exception as e:
            print('problem marking all notifs read: %s' % e)
