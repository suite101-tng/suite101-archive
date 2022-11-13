import re
from django import template

register = template.Library()


def noimage(data):
    p = re.compile(r'<img.*/?>')
    return p.sub('', data)
register.filter(noimage)
