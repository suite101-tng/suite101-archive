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

def validate_pw_reset_key(reset_key, user=None):
    '''validate the password reset key and return its user'''
    User = get_user_model()
    if not reset_key:
        return None
    try:
        user_from_key = User.objects.get(reset_key=reset_key)
    except Exception as e:
        return None

    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    if not user_from_key.reset_time or user_from_key.reset_time < yesterday:
        return None
    
    if user and user.is_authenticated():
        if not user == user_from_key:
            return None
    return user_from_key
