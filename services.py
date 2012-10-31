from moxie.core.service import Service
from moxie.library.providers.oxford_z3950 import LibrarySearchQuery


class LibrarySearchService(Service):

    def search(self, title, author, isbn):
        z = self.get_provider(None)
        q = LibrarySearchQuery(title, author, isbn)
        # TODO augment with Places service for location-based information
        return z.library_search(q)