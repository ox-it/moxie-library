import hashlib
import json
import logging

from flask import request, abort, url_for

from moxie.core.views import ServiceView
from moxie.core.kv import kv_store
from moxie.library.services import LibrarySearchService

logger = logging.getLogger(__name__)


class Search(ServiceView):

    CACHE_KEY_FORMAT = '{0}_library_{1}'
    CACHE_EXPIRE = 120   # seconds for cache to expire

    def handle_request(self):
        # 1. Request from Service
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)

        # TODO shouldn't be as general as Exception, could be Bad Request if it's inconsistent query
        # or Service Unavailable if the service is... not available...
        try:
            results = self.get_search_result(title, author, isbn)
        except Exception as e:
            abort(400, description=e.message)
        else:
            # 2. Do pagination
            start = int(request.args.get('start', 0))
            count = int(request.args.get('count', 10))

            context = { 'size': len(results),
                        'results': results[start:(start+count)] }
            if len(results) > start+count:
                context['links'] = { 'next': url_for('.search', title=title, author=author, isbn=isbn, start=start+count, count=count)}
            return context

    def get_search_result(self, title, author, isbn):
        """Check the cache or call the service to retrieve
        search results
        :param title: search title
        :param author: search author
        :param isbn: search isbn
        :return list of results
        """
        search_string = "{0}{1}{2}".format(removeNonAscii(title), removeNonAscii(author), removeNonAscii(isbn))
        hash = hashlib.md5()
        hash.update(search_string)
        service = LibrarySearchService.from_context()
        cache = kv_store.get(self.CACHE_KEY_FORMAT.format(__name__, hash.hexdigest()))
        if cache:
            logger.debug("Search results from cache")
            return json.loads(cache)
        else:
            logger.debug("Search results from service")
            results = service.search(title, author, isbn)
            kv_store.setex(self.CACHE_KEY_FORMAT.format(__name__, hash.hexdigest()), self.CACHE_EXPIRE, json.dumps(results))
            return results


def removeNonAscii(s):
    if s:
        return "".join(i for i in s if ord(i)<128)
    else:
        return ""


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        service = LibrarySearchService.from_context()
        result = service.get_media(id)
        return result