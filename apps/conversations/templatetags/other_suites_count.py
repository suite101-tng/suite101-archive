from django import template
register = template.Library()


def other_suites_count(suites):
    if suites.count() > 1:
        return suites.count() - 1
    return 0

register.filter(other_suites_count)
