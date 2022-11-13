import re
from django import template
from django.utils.safestring import mark_safe


BOLD_RE = re.compile(u'<\/?(strong|b)>',
                         re.UNICODE | re.IGNORECASE)

    #(<a\s*(?!.*\brel=)[^>]*)(href="https?://)((?!blog.bandit.co.nz)[^"]+)"([^>]*)>#gi

register = template.Library()

def strip_strong_bold(content):
    # return content
    return mark_safe(re.sub(BOLD_RE, '', content))
register.filter(strip_strong_bold)
