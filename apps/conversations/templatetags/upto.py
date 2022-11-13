from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def upto(value, delimiter=None):
    """ http://stackoverflow.com/questions/6481788/format-of-timesince-filter """
    return value.split(delimiter)[0]
upto.is_safe = True