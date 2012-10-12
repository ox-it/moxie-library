from flask import Blueprint

from .views import Search, ResourceDetail

library_blueprint = Blueprint('library', __name__)

# URL Rules
library_blueprint.add_url_rule('/search',
        view_func=Search.as_view('search'))

library_blueprint.add_url_rule('/<path:id>',
        view_func=ResourceDetail.as_view('resourcedetail'))
