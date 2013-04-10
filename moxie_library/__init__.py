from flask import Blueprint, request
from flask.helpers import make_response

from moxie.core.representations import HALRepresentation
from .views import Search, ResourceDetail


def create_blueprint(blueprint_name):
    library_blueprint = Blueprint(blueprint_name, __name__)

    library_blueprint.add_url_rule('/', view_func=get_routes)

    library_blueprint.add_url_rule('/search',
            view_func=Search.as_view('search'))
    library_blueprint.add_url_rule('/item:<string:id>/',
            view_func=ResourceDetail.as_view('item'))
    return library_blueprint


def get_routes():
    path = request.path
    representation = HALRepresentation({})
    representation.add_curie('hl', 'http://moxie.readthedocs.org/en/latest/http_api/library.html#{rel}')
    representation.add_link('self', '{bp}'.format(bp=path))
    representation.add_link('hl:search', '{bp}search?title={{title}}&author={{author}}&isbn={{isbn}}'.format(bp=path),
                            templated=True, title='Search')
    representation.add_link('hl:item', '{bp}item:{{id}}'.format(bp=path),
                            templated=True, title='POI detail')
    response = make_response(representation.as_json(), 200)
    response.headers['Content-Type'] = "application/json"
    return response