import logging

from flask import request, abort

from moxie.core.views import ServiceView, accepts
from moxie.core.representations import JSON, HAL_JSON
from moxie_library.representations import JsonItemRepresentation, JsonItemsRepresentation, HalJsonItemsRepresentation, HalJsonItemRepresentation
from moxie_library.services import LibrarySearchService
from moxie_library.domain import LibrarySearchQuery, LibrarySearchException

logger = logging.getLogger(__name__)


class Search(ServiceView):

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
        except LibrarySearchException as e:
            abort(500, description=e.msg)
        except LibrarySearchQuery.InconsistentQuery as e:
            abort(400, description=e.msg)
        else:
            # 2. Do pagination
             return { 'size': size,
                        'results': results}

    @accepts(JSON)
    def as_json(self, response):
        return JsonItemsRepresentation(self.title, self.author, self.isbn,
            response['results'], response['size']).as_json()

    @accepts(HAL_JSON)
    def as_hal_json(self, response):
        return HalJsonItemsRepresentation(self.title, self.author, self.isbn,
            response['results'], self.start, self.count, response['size'],
            request.url_rule.endpoint).as_json()


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        availability = get_boolean_value(request.args.get('availability', 'true'))
        result = service.get_media(id, availability)
        return result

    @accepts(JSON)
    def as_json(self, response):
        return JsonItemRepresentation(response).as_json()

    @accepts(HAL_JSON)
    def as_hal_json(self, response):
        return HalJsonItemRepresentation(response, request.url_rule.endpoint).as_json()


def get_boolean_value(s, default=False):
    s = s.lower()
    if s == 'true':
        return True
    elif s == 'false':
        return False
    return default