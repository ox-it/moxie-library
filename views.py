from flask import request, abort

from moxie.core.views import ServiceView
from moxie.library.providers.oxford_z3950 import Z3950, LibrarySearchQuery


class Search(ServiceView):

    def handle_request(self):
        title = request.args.get('title', None)
        author = request.args.get('author', None)
        isbn = request.args.get('isbn', None)

        z = Z3950('library.ox.ac.uk', 'ALEPH', results_encoding='unicode')
        q = LibrarySearchQuery(title, author, isbn)
        results = z.library_search(q)
        page = []
        for r in results[0:10]:
            page.append(r.simplify_for_render())
        context = { 'results': page }
        return context


class ResourceDetail(ServiceView):

    def handle_request(self, id):
        pass