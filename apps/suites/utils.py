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
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from suites.models import SuitePost, Suite
from articles.models import Article

from lib.enums import *
# from zbase32 import *
from project import settings
logger = logging.getLogger(__name__)

def get_nearby_suite_posts(user, suite_post):
    ''' do we have similar SuitePost events? do tell. '''

    others = similar_type = similar_count = primary_similar_obj = None

    similar_within = 1 # day
    similarity_threshold = suite_post.created - datetime.timedelta(days=similar_within)

    others = SuitePost.objects.filter(suite=suite_post.suite, added_by=user, created__gte=similarity_threshold).exclude(pk=suite_post.pk).order_by('-created')
    if not others:
        return None
    return others
