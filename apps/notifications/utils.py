import json, time, datetime, logging
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
from notifications.models import *
from notifications.tasks import fanout_notification

from lib.enums import *
# from zbase32 import *
from project import settings
logger = logging.getLogger(__name__)

def new_notification(content_object, fanout_list, chat_type=False, mod_type=False, date=None):
    if not fanout_list or not content_object:
        return

    # we assume content_object is an instance of a TimeStampedModel if not date
    if not date:
        try:
            date = content_object.created
        except:
            return

    try:
        notif, created = Notification.objects.get_or_create(content_type=ContentType.objects.get_for_model(content_object),object_id=content_object.pk)
        notif.date = date # add or update the date
        notif.mod_type = mod_type
        notif.chat_type = chat_type
        notif.save()
    except Exception as e:
        print('problem creating notication object: %s' % e)
        logger.error(e)
        return

    if not notif:
        return

    fanout_notification(notif, fanout_list)
