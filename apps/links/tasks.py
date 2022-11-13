from __future__ import division
import celery
import datetime
from django.contrib.auth import get_user_model
from lib.cache import get_object_from_pk
from django.http import HttpResponse
from django.db.models import Sum, Count
from .sets import *

# @celery.task(name='links.tasks.name_of_task')
# def name_of_task():
    # do some things