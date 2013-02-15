import logging

from moxie.core.service import Service
from moxie_library.domain import LibrarySearchQuery, LibrarySearchException

logger = logging.getLogger(__name__)


class LibrarySearchService(Service):
    """Library search service
    """

    def __init__(self, search_provider_config=None):
        self.searcher = self._import_provider(search_provider_config.items()[0])

    def search(self, title, author, isbn, availability, start=0, count=10):
        """Search for media in the given provider.
        :param title: title
        :param author: author
        :param isbn: isbn
        :param availability: annotate result with availability information
        :param start: first result to return
        :param count: number of results to return
        :return list of results
        """

        query = LibrarySearchQuery(title, author, isbn)
        try:
            size, results = self.searcher.library_search(query, start, count, availability=availability)
        except LibrarySearchException as lse:
            raise lse   # TODO raise application exception
        return size, results

    def get_media(self, control_number, availability):
        """Get a media by its control number
        :param control_number: ID of the media
        :param availability: annotate item with availability information
        :return result or None
        """
        try:
            return self.searcher.control_number_search(control_number, availability=availability)
        except LibrarySearchException as lse:
            raise lse   # TODO raise application exception


def removeNonAscii(s):
    if s:
        return "".join(i for i in s if ord(i) < 128)
    else:
        return ""
