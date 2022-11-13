from functools import wraps

from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.utils.decorators import available_attrs


def ajax_login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request or not request.user:
            if request.is_ajax():
                return HttpResponseForbidden()
            else:
                return HttpResponseRedirect(reverse('login'))

        if not request.user.is_authenticated():
            if request.is_ajax():
                return HttpResponseForbidden()
            else:
                return HttpResponseRedirect(reverse('login'))

        return view_func(request, *args, **kwargs)
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)