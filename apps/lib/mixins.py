import json
import logging

from django.http import HttpResponse

from lib.cache import get_object_from_slug, get_object_from_pk

logger = logging.getLogger(__name__)


class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    def form_invalid(self, form, extra_data={}):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            if extra_data:
                for key, value in extra_data.items():
                    form.errors[key] = value

            return self.render_to_json_response(form.errors, status=400)
        else:
            return response

    def form_valid(self, form, extra_data={}):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            try:
                data = {
                    'pk': self.object.pk,
                }
            except:
                data = {}
                pass

            try:
                data['slug'] = self.object.slug
            except:
                pass
            try:
                data['name'] = self.object.name
            except:
                pass

            if extra_data:
                for key, value in extra_data.items():
                    data[key] = value

            return self.render_to_json_response(data)
        else:
            return response

    def delete(self, request, *args, **kwargs):
        response = super(AjaxableResponseMixin, self).delete(request, *args, **kwargs)
        if self.request.is_ajax():
            return self.render_to_json_response('ok')
        else:
            return response


class CachedObjectMixin(object):
    """
    Mixin for grabbing an object from cache before attempting to
    grab it from the database.
    This mixin also takes care of calling the model invalidation
    when/if a form is valid (ie. model is being saved)
    """
    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)

        if pk is not None:
            obj = get_object_from_pk(self.model, pk)
        elif slug is not None:
            obj = get_object_from_slug(self.model, slug)
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)
        return obj

    def form_valid(self, form):
        response = super(CachedObjectMixin, self).form_valid(form)
        try:
            self.object.invalidate()
        except Exception as e:
            logger.error(e)
            pass
        return response
