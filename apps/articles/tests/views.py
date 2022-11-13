import json
import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django_nose.tools import *

from lib.tests import Suite101BaseTestCase
from articles.utils import *
from articles.models import *
from suites.models import Suite, SuitePost


