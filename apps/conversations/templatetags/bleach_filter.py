import bleach
from django import template
from django.utils.safestring import mark_safe
register = template.Library()

ALLOWED_TAGS = [
    'a',
    'abbr',
    'h2',
    'acronym',
    'blockquote',
    'code',
    'pre',
    'em',
    'hr',
    'i',
    'li',
    'ol',
    'p',
    'ul',
    'figure',
    'figcaption',
    'div',
    'img',
    'br',
    'b',
    'iframe',
]
ALLOWED_ATTRIBUTES = {
    'a': [
        'href',
        'title',
        'rel',
        'target'
    ],
    'acronym': ['title'],
    'abbr': ['title'],
    'iframe': [
        'class',
        'src',
        'data-orig-url',
        'width',
        'height',
        'scrolling'
        'frameborder',
        'allowfullscreen',
    ],
    'div': [
        'class',
    ],
    'figcaption': [
        'class',
        'contenteditable',
        'unselectable',
        'data-id',
        'data-type'
    ],
    'figure': [
        'class',
        'contenteditable',
        'unselectable',
        'data-id',
        'data-type'
    ],
    'blockquote': [
        'class',
        'lang'
        ],
    'img': [
        'class',
        'src',
        'data-caption',
        'data-credit',
        'data-credit-link',
        'data-height',
        'data-width',
        'data-type',
        'title',
        'alt'
    ],
    'p': [
        'style',
        'lang',
        'class',
        'dir'
    ]}
ALLOWED_STYLES = [
    'text-align'
]
def bleach_filter(body, allowed=None):
    if allowed:
        bleached_body = bleach.clean(body, allowed, ALLOWED_ATTRIBUTES, ALLOWED_STYLES, strip=True)
    else:
        bleached_body = bleach.clean(body, ALLOWED_TAGS, ALLOWED_ATTRIBUTES, ALLOWED_STYLES, strip=True)
    return mark_safe(bleached_body)
register.filter(bleach_filter)
