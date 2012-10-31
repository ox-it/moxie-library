from moxie.core.service import Service
from moxie.library.providers.oxford_z3950 import LibrarySearchQuery
from moxie.places.services import POIService


class LibrarySearchService(Service):
    """Library search service
    """

    def search(self, title, author, isbn):
        """Search for media in the given provider.
        :param title: title
        :param author: author
        :param isbn: isbn
        :return list of results
        """
        z = self.get_provider(None)
        q = LibrarySearchQuery(title, author, isbn)
        poi_service = POIService.from_context()
        results = z.library_search(q)
        for result in results:
            for location in result['holdings']:
                poi = poi_service.get_place_by_identifier('olis-aleph:{0}'.format(location.replace('/', '\/')))
                if poi:
                    result['holdings'][location].append(poi)
        return results