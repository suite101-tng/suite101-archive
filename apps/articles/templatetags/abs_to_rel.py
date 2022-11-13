import re
from django import template
from django.utils.safestring import mark_safe


SUITE_ABS = re.compile(u'href=(?P<startquote>[\"\']?)https?://([a-zA-Z0-9]+\.)?suite101\.com/',
                         re.UNICODE | re.IGNORECASE)

    #(<a\s*(?!.*\brel=)[^>]*)(href="https?://)((?!blog.bandit.co.nz)[^"]+)"([^>]*)>#gi

register = template.Library()

def repl(matchobj):
    if matchobj and matchobj.group('startquote'):
        return 'href=' + matchobj.group('startquote') + '/'
    else: 
        return 'href=/'


def abs_to_rel(content):
    # return content
    return mark_safe(re.sub(SUITE_ABS, repl, content))
register.filter(abs_to_rel)
