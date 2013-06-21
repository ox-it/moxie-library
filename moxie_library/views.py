import logging

from flask import request

from moxie.core.views import ServiceView, accepts
from moxie.core.cache import cache, args_cache_key
from moxie.core.exceptions import BadRequest, NotFound
from moxie.core.representations import JSON, HAL_JSON
from moxie_library.domain import LibrarySearchException, LibrarySearchQuery
from moxie_library.representations import HALItemsRepresentation, HALItemRepresentation
from moxie_library.services import LibrarySearchService

logger = logging.getLogger(__name__)


class Search(ServiceView):

    @cache.cached(timeout=60, key_prefix=args_cache_key)
    def handle_request(self):
        # 1. Request from Service
        self.title = request.args.get('title', None)
        self.author = request.args.get('author', None)
        self.isbn = request.args.get('isbn', None)
        self.availability = get_boolean_value(request.args.get('availability', 'false'))
        self.start = int(request.args.get('start', 0))
        self.count = int(request.args.get('count', 35))

        try:
            service = LibrarySearchService.from_context()
            size, results = service.search(self.title, self.author, self.isbn,
                                           self.availability, self.start, self.count)
            results = list(results)     # necessary for caching (cannot pickle with generators)
        except LibrarySearchQuery.InconsistentQuery as e:
            raise BadRequest(message=e.msg)
        else:
            return {'size': size, 'results': results, 'title': self.title,
                    'author': self.author, 'isbn': self.isbn,
                    'start': self.start, 'count': self.count}

    @accepts(HAL_JSON, JSON)
    def as_hal_json(self, response):
        return HALItemsRepresentation(response['title'], response['author'], response['isbn'],
                                      response['results'], response['start'], response['count'], response['size'],
                                      request.url_rule.endpoint).as_json()


class ResourceDetail(ServiceView):

    @cache.cached(timeout=60)
    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        availability = get_boolean_value(request.args.get('availability', 'true'))
        result = service.get_media(id, availability)
        if not result:
            raise NotFound()
        return result

    @accepts(HAL_JSON, JSON)
    def as_hal_json(self, response):
        return HALItemRepresentation(response, request.url_rule.endpoint).as_json()


def get_boolean_value(s, default=False):
    s = s.lower()
    if s == 'true':
        return True
    elif s == 'false':
        return False
    return default