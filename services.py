import hashlib
import logging
import json

from flask import url_for

from moxie.core.service import Service
from moxie.core.kv import kv_store
from moxie.library.providers.oxford_z3950 import LibrarySearchQuery
from moxie.places.services import POIService
from moxie.places.importers.helpers import simplify_doc_for_render

logger = logging.getLogger(__name__)


class LibrarySearchService(Service):
    """Library search service
    """

    CACHE_KEY_FORMAT = '{0}_library_search_{1}'
    CACHE_EXPIRE = 120   # seconds for cache to expire

    def __init__(self, providers=None):
        self.providers = providers or []

    def get_provider(self):
        """Get a provider for searching libraries
        TODO this currently returns the first provider in the list
        """
        return self.providers[0]

    def search(self, title, author, isbn, start=0, count=10, no_cache=False):
        """Search for media in the given provider.
        :param title: title
        :param author: author
        :param isbn: isbn
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
            provider = self.get_provider()
            query = LibrarySearchQuery(title, author, isbn)
            results = provider.library_search(query)
            kv_store.setex(self.CACHE_KEY_FORMAT.format(__name__, hash.hexdigest()), self.CACHE_EXPIRE, json.dumps(results))

        poi_service = POIService.from_context()

        page = list()

        for result in results[start:(start+count)]:
            result['links'] = { 'self': url_for('library.resourcedetail', id=result['control_number']) }
            for location in result['holdings']:
                # TODO place identifier has to be set in configuration (__init__)
                poi = poi_service.search_place_by_identifier('olis-aleph:{0}'.format(location.replace('/', '\/')))
                if poi:
                    result['holdings'][location]['poi'] = simplify_doc_for_render(poi)
            page.append(result)
        return len(results), page

    def get_media(self, control_number):
        """Get a media by its control number
        :param control_number: ID of the media
        :return result or None
        """
        z = self.get_provider()
        result = z.control_number_search(control_number)
        return result


def removeNonAscii(s):
    if s:
        return "".join(i for i in s if ord(i)<128)
    else:
        return ""