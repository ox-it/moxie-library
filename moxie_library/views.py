import logging

from flask import request, abort, url_for

from moxie.core.views import ServiceView
from moxie.library.services import LibrarySearchService
from moxie.library.providers.oxford_z3950 import LibrarySearchException
from moxie.library.providers.oxford_z3950 import LibrarySearchQuery

logger = logging.getLogger(__name__)


class Search(ServiceView):

    def handle_request(self):
        # 1. Request from Service
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)
        start = int(request.args.get('start', 0))
        count = int(request.args.get('count', 10))

        # TODO extract these exceptions from the provider
        try:
            service = LibrarySearchService.from_context()
            size, results = service.search(title, author, isbn, start, count)
        except LibrarySearchException as e:
            abort(500, description=e.msg)
        except LibrarySearchQuery.InconsistentQuery as e:
            abort(400, description=e.msg)
        else:
            # 2. Do pagination
            context = { 'size': size,
                        'results': results,
                        'links': dict()}
            if size > start+count:
                context['links']['next'] = url_for('.search', title=title, author=author, isbn=isbn, start=start+count, count=count)
            if start > 0 and size > start+count:
                context['links']['prev'] = url_for('.search', title=title, author=author, isbn=isbn, start=start-count, count=count)
            context['links']['last'] = url_for('.search', title=title, author=author, isbn=isbn, start=size-count, count=count)
            context['links']['first'] = url_for('.search', title=title, author=author, isbn=isbn, count=count)
            return context


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        result = service.get_media(id)
        return result