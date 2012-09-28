from flask import Blueprint

from .views import Search, ResourceDetail

library = Blueprint('library', __name__)

# URL Rules
library.add_url_rule('/search', view_func=Search.as_view('search'))
library.add_url_rule('/<path:id>', view_func=ResourceDetail.as_view('resourcedetail'))