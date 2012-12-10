from flask import Blueprint

from .views import Search, ResourceDetail


def create_blueprint(blueprint_name):
    library_blueprint = Blueprint(blueprint_name, __name__)

    # URL Rules
    library_blueprint.add_url_rule('/search',
            view_func=Search.as_view('search'))
    library_blueprint.add_url_rule('/item:<path:id>',
            view_func=ResourceDetail.as_view('resourcedetail'))
    return library_blueprint
