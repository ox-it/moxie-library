import logging

from flask import request, abort, url_for

from moxie.core.views import ServiceView
from moxie.library.services import LibrarySearchService

logger = logging.getLogger(__name__)


class Search(ServiceView):

    def handle_request(self):
        # 1. Request from Service
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)
        start = int(request.args.get('start', 0))
        count = int(request.args.get('count', 10))

        # TODO shouldn't be as general as Exception, could be Bad Request if it's inconsistent query
        # or Service Unavailable if the service is... not available...
        try:
            service = LibrarySearchService.from_context()
            size, results = service.search(title, author, isbn, start, count)
        except Exception as e:
            abort(400, description=e.message)
        else:
            # 2. Do pagination
            context = { 'size': size,
                        'results': results,
                        'links': dict()}
            # TODO add links: prev, last in addition to next
            if size > start+count:
                context['links']['next'] = url_for('.search', title=title, author=author, isbn=isbn, start=start+count, count=count)
            if count > 0 and size > start+count:
                context['links']['prev'] = url_for('.search', title=title, author=author, isbn=isbn, start=start-count, count=count)
            context['links']['last'] = url_for('.search', title=title, author=author, isbn=isbn, start=size-count, count=count)
            context['links']['first'] = url_for('.search', title=title, author=author, isbn=isbn, count=count)
            return context


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        result = service.get_media(id)
        return result