import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def header_sub(match):
    if match and match.group('text'):
        return '<h2>' + match.group('text') + '</h2>'
    else:
        return ''

def bio(bio):
    if bio == '<p><br></p>':
        new_bio = bio.replace('<p><br></p>', '')
        return mark_safe(new_bio)
    else:
        return bio

def ptag(body, article):
    if article.archive and article.created == article.saved_on:
        if '<p>' in body:
            # strip excess linebreaks and empty p tags then
            new_body = body.replace('\r\n', ' ')
            return mark_safe(re.sub(r'<p>\s*</p>', '', new_body))

        body_arr = body.split('\r\n\r\n')
        if len(body_arr) == 1:
            body_arr = body.split('<br><br>')
        if len(body_arr) == 1:
            body_arr = body.split('<br/><br/>')

        return_val = ''
        for segment in body_arr:
            segment = re.sub(r'<(strong|b)\b[^>]*>(?P<text>.*?)<\/(strong|b)>$', header_sub, segment)
            if not segment == '' and not 'h2' in segment:
                return_val += '<p>' + segment + '</p>'
            else:
                return_val += segment
        return mark_safe(return_val)
    else:
        return body



register.filter(ptag)
