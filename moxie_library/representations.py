from flask import url_for, jsonify

from moxie.core.representations import JsonRepresentation, HalJsonRepresentation, get_nav_links


class JsonItemRepresentation(JsonRepresentation):

    def __init__(self, item):
        self.item = item

    def as_dict(self):
        return {
            'id': self.item.control_number,
            'title': self.item.title,
            'author': self.item.author,
        }

    def as_json(self):
        return jsonify(self.as_dict())


class HalJsonItemRepresentation(JsonItemRepresentation):

    def __init__(self, item, endpoint):
        super(HalJsonItemRepresentation, self).__init__(item)
        self.endpoint = endpoint

    def as_dict(self):
        base = super(HalJsonItemRepresentation, self).as_dict()
        links = { 'self': {
                    'href': url_for(self.endpoint, id=self.item.id)
                }
        }
        return HalJsonRepresentation(base, links).as_dict()

    def as_json(self):
        return jsonify(self.as_dict())


class JsonItemsRepresentation(object):

    def __init__(self, search, results):
        self.search = search
        self.results = results

    def as_dict(self, representation=JsonItemRepresentation):
        return {'query': self.search,
                'results': [representation(r).as_dict() for r in self.results]}

    def as_json(self):
        return jsonify(self.as_dict())


class HalJsonItemsRepresentation(JsonItemsRepresentation):

    def __init__(self, search, results, start, count, size, endpoint):
        super(HalJsonItemsRepresentation, self).__init__(search, results)
        self.start = start
        self.count = count
        self.size = size
        self.endpoint = endpoint

    def as_dict(self):
        response = {
            'query': self.search,
            'size': self.size,
        }
        items = [HalJsonItemRepresentation(r, 'library.resourcedetail').as_dict() for r in self.results]
        links = {'self': {
                    'href': url_for(self.endpoint, q=self.search)
            }
        }
        links.update(get_nav_links(self.endpoint, self.start, self.count, self.size, q=self.search))
        return HalJsonRepresentation(response, links, {'items': items}).as_dict()

    def as_json(self):
        return jsonify(self.as_dict())