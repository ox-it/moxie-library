from flask import request, abort

from moxie.core.views import ServiceView

class Search(ServiceView):

    def handle_request(self):
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)

        if not title or not author or not isbn:
            abort(400)
        else:
            pass


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        pass