import re
from django import template

register = template.Library()


def space_to_dash(text):
    filtered = text.replace(' ', '-') \
        .replace('&rdquo', '') \
        .replace('&rdquo', '') \
        .replace('&middot', '')
    return re.sub('[^-\w]', '', filtered)

register.filter(space_to_dash)
