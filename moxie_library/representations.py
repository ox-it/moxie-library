from flask import url_for, jsonify

from moxie.core.representations import JsonRepresentation, HalJsonRepresentation, get_nav_links
from moxie.core.service import NoConfiguredService
from moxie.places.services import POIService
from moxie.places.representations import HalJsonPoiRepresentation


class JsonItemRepresentation(JsonRepresentation):

    def __init__(self, item):
        self.item = item

    def as_dict(self):
        return {
            'id': self.item.control_number,
            'title': self.item.title,
            'author': self.item.author,
            'publisher': self.item.publisher,
            'description': self.item.description,
            'edition': self.item.edition,
            'copies': self.item.copies,
            'holdings': self.item.libraries,
            'isbns': self.item.isbns,
            'issns': self.item.issns,
        }

    def as_json(self):
        return jsonify(self.as_dict())


class HalJsonItemRepresentation(JsonItemRepresentation):

    def __init__(self, item, endpoint, place_identifier='olis-aleph'):
        """HAL Json representation for an item
        :param item: domain item to represent
        :param endpoint: base endpoint (URL)
        :param place_identifier: identifier when searching for places
        """
        super(HalJsonItemRepresentation, self).__init__(item)
        self.endpoint = endpoint
        self.place_identifier = place_identifier

    def as_dict(self):
        base = super(HalJsonItemRepresentation, self).as_dict()
        links = { 'self': {
                    'href': url_for(self.endpoint, id=self.item.control_number)
                }
        }

        embedded = None

        try:
            poi_service = POIService.from_context()
        except NoConfiguredService:
            pass
        else:
            embedded = {}
            for location in self.item.libraries:
                poi = poi_service.search_place_by_identifier('{key}:{value}'
                    .format(key=self.place_identifier, value=location.replace('/', '-')))
                if poi:
                    embedded[location] = HalJsonPoiRepresentation(poi, 'places.poidetail').as_dict()
        return HalJsonRepresentation(base, links, embedded).as_dict()

    def as_json(self):
        return jsonify(self.as_dict())


class JsonItemsRepresentation(object):

    def __init__(self, title, author, isbn, results, size):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.results = results
        self.size = size

    def as_dict(self, representation=JsonItemRepresentation):
        return {'title': self.title,
                'author': self.author,
                'isbn': self.isbn,
                'size': self.size,
                'results': [representation(r).as_dict() for r in self.results]}

    def as_json(self):
        return jsonify(self.as_dict())


class HalJsonItemsRepresentation(JsonItemsRepresentation):

    def __init__(self, title, author, isbn, results, start, count, size, endpoint):
        super(HalJsonItemsRepresentation, self).__init__(title, author, isbn, results, size)
        self.start = start
        self.count = count
        self.endpoint = endpoint

    def as_dict(self):
        response = {
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'size': self.size,
        }
        items = [HalJsonItemRepresentation(r, 'library.item').as_dict() for r in self.results]
        links = {'self': {
                    'href': url_for(self.endpoint, title=self.title, author=self.author, isbn=self.isbn)
            }
        }
        links.update(get_nav_links(self.endpoint, self.start, self.count, self.size,
            title=self.title, author=self.author, isbn=self.isbn))
        return HalJsonRepresentation(response, links, {'items': items}).as_dict()

    def as_json(self):
        return jsonify(self.as_dict())