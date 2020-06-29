# coding: utf-8

from django.conf import settings
from django.conf.urls.defaults import include, patterns

from djcommon.helpers import construct_object


class ProductListFiltersMiddleware(object):
    """
    Middleware to set up ProductListFilters urls on incoming request.
    """
    def __init__(self):
        self.override_url = True

    def process_request(self, request):
        if self.override_url:
            try:
                original_urlconf = __import__(getattr(request, 'urlconf', settings.ROOT_URLCONF), {}, {}, ['*'])
            except TypeError:
                original_urlconf = request.urlconf
            for filter_location in settings.PRODUCT_LIST_FILTERS:
                filter = construct_object(filter_location, **{'queryset': None, 'request': request, 'view': 'novomore.apps.catalog.views.product_showcase_list'})
                if hasattr(filter, 'get_urls'):
                    original_urlconf.urlpatterns = filter.get_urls() + original_urlconf.urlpatterns

            self.override_url = False
            request.urlconf = original_urlconf
