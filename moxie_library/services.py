import hashlib
import logging
import json

from moxie.core.service import Service
from moxie.core.kv import kv_store
from moxie_library.domain import LibrarySearchQuery

logger = logging.getLogger(__name__)


class LibrarySearchService(Service):
    """Library search service
    """

    CACHE_KEY_FORMAT = '{0}_library_search_{1}'
    CACHE_EXPIRE = 120   # seconds for cache to expire

    def __init__(self, search_provider_config=None):
        self.searcher = self._import_provider(search_provider_config.items()[0])

    def search(self, title, author, isbn, availability, start=0, count=10, no_cache=False):
        """Search for media in the given provider.
        :param title: title
        :param author: author
        :param isbn: isbn
        :param availability: annotate result with availability information
        :param start: first result to return
        :param count: number of results to return
        :param no_cache: do not use the (potentially) cached result
        :return list of results
        """
        search_string = "{0}{1}{2}".format(removeNonAscii(title), removeNonAscii(author), removeNonAscii(isbn))
        hash = hashlib.md5()
        hash.update(search_string)
        cache = kv_store.get(self.CACHE_KEY_FORMAT.format(__name__, hash.hexdigest()))
        if cache and not no_cache:
            results = json.loads(cache)
        else:
            query = LibrarySearchQuery(title, author, isbn)
            results = self.searcher.library_search(query)
            #kv_store.setex(self.CACHE_KEY_FORMAT.format(__name__, hash.hexdigest()), self.CACHE_EXPIRE, json.dumps(results))

        return len(results), results[start:(start+count)]

    def get_media(self, control_number, availability):
        """Get a media by its control number
        :param control_number: ID of the media
        :param availability: annotate item with availability information
        :return result or None
        """
        result = self.searcher.control_number_search(control_number, availability=availability)
        return result


def removeNonAscii(s):
    if s:
        return "".join(i for i in s if ord(i)<128)
    else:
        return ""
