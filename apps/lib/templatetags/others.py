from datetime import datetime
from django.template.defaultfilters import timesince
from django.utils import timesince
import re
from django import template

register = template.Library()


@register.filter(name='others')
def others(objects, num):
    return len(objects) - int(num)


@register.filter(name='print_timestamp')
def print_timestamp(timestamp):
    try:
        #assume, that timestamp is given in seconds with decimal point
        ts = float(timestamp)
    except ValueError:
        return None
    return datetime.datetime.fromtimestamp(ts)

@register.filter(name='random_number')
def random_number(high):
    from random import randint
    return randint(0,high)

@register.filter(name='googleplus_url')
def googleplus_url(url):
    query_re = re.compile('.+\?.+',
                         re.UNICODE | re.IGNORECASE)
    authorship_re = re.compile('.+([\?&]rel=author)',
                         re.UNICODE | re.IGNORECASE)
    if re.match(query_re, url) and re.match(authorship_re, url): # we're good, return url
        return url
    elif re.match(query_re, url):
        return url + '&rel=author'
    return url + '?rel=author'


@register.filter
def leading_zeros(value, desired_digits):
    """
    Given an integer, returns a string representation, padded with [desired_digits] zeros.
    """
    num_zeros = int(desired_digits) - len(value)
    padded_value = []
    while num_zeros >= 1:
        padded_value.append("0") 
        num_zeros = num_zeros - 1
    return ",".join(padded_value)

@register.filter(name='strtotimesince')
def strtotimesince(value,format=None):
    from django.utils import timesince
    from django.template.defaultfilters import stringfilter
    if not value:
        return u''

    if not format:
        format = "%a %b %d %H:%M:%S +0000 %Y"
    try:
        convert_to_datetime = datetime.strptime(value, format)
        if convert_to_datetime:
            return "%s ago" % timesince.timesince(convert_to_datetime).split(',')[0]
    except Exception as e:
        return ''


@register.filter
def add_http(url):
    if not 'http' in url:
        return 'http:%s' % url
    return url


@register.filter(name='percentage')  
def percentage(value):  
    try:  
        return round((value * 100),1)
    except ValueError:  
        return '' 