import logging

from flask import request, abort

from moxie.core.views import ServiceView, accepts
from moxie.core.representations import JSON, HAL_JSON
from moxie_library.representations import JsonItemRepresentation, JsonItemsRepresentation, HalJsonItemsRepresentation
from moxie_library.services import LibrarySearchService
from moxie_library.domain import LibrarySearchQuery, LibrarySearchException

logger = logging.getLogger(__name__)


class Search(ServiceView):

    def handle_request(self):
        # 1. Request from Service
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)
        self.start = int(request.args.get('start', 0))
        self.count = int(request.args.get('count', 10))

        try:
            service = LibrarySearchService.from_context()
            size, results = service.search(title, author, isbn, self.start, self.count)
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
        return JsonItemsRepresentation("search", response['results']).as_json()

    @accepts(HAL_JSON)
    def as_hal_json(self, response):
        return HalJsonItemsRepresentation('search', response['results'], self.start,
            self.count, response['size'], request.url_rule.endpoint).as_json()


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        result = service.get_media(id)
        return result