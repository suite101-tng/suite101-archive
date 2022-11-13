import re
from django import template
from django.utils.safestring import mark_safe

NOFOLLOW_RE = re.compile(u'<a (?![^>]*rel=["\']nofollow[\'"])'
                         u'(?![^>]*href=["\']\.{0,2}/[^/])'
                         u'(?![^>]*href=["\']https?://([a-bA-Z1-9]+\.)?suite\.io)',
                         re.UNICODE | re.IGNORECASE)

    #(<a\s*(?!.*\brel=)[^>]*)(href="https?://)((?!blog.bandit.co.nz)[^"]+)"([^>]*)>#gi

register = template.Library()

def nofollow(content, author):
    return mark_safe(re.sub(NOFOLLOW_RE, u'<a target="_blank" rel="nofollow" ', content))
register.filter(nofollow)
