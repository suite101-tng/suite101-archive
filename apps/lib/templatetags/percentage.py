from django import template
register = template.Library()


@register.filter(name='percentage')
def percentage(number):
    # import pdb; pdb.set_trace()
    try:
        return "%.2f%%" % (number * 100.0)
    except (ValueError, ZeroDivisionError):
        return ""