from PyZ3950 import zoom

class Z3950(object):

    class Results:
        """
        A thing that pretends to be a list for lazy parsing of search results
        """

        def __init__(self, results, wrapper, results_encoding):
            self.results = results
            self._wrapper = wrapper
            self._results_encoding = results_encoding

        def __iter__(self):
            for result in self.results:
                yield self._wrapper(result,
                    results_encoding=self._results_encoding)

        def __len__(self):
            return len(self.results)

        def __getitem__(self, key):
            if isinstance(key, slice):
                if key.step:
                    raise NotImplementedError("Stepping not supported")
                return (self._wrapper(r, results_encoding=self._results_encoding)\
                    for r in self.results.__getslice__(key.start, key.stop))
            else:
                return self._wrapper(self.results[key],
                    results_encoding=self._results_encoding)

    def __init__(self, host, database, port=210, syntax='USMARC',
                 charset='UTF-8', control_number_key='12',
                 results_encoding='marc8'):
        """
        @param host: The hostname of the Z39.50 instance to connect to
        @type host: str
        @param database: The database name
        @type database: str
        @param port: An optional port for the Z39.50 database
        @type port: int
        @param syntax: The Z39.50 syntax to use, or an object which does parsing
                       of the result
        @type syntax: str or object
        @param charset: The charset to make the connection in
        @type charset: str
        @param control_number_key: The use attribute for the control number when
                                   querying
        @param results_encoding: The encoding (either unicode or marc8) of data
                                 this server returns
        """

        # Could create a persistent connection here
        self._host = host
        self._database = database
        self._port = port
        self._syntax = syntax
        self._wrapper = {
            'USMARC': USMARCSearchResult,
            'XML': XMLSearchResult,
            }.get(syntax, syntax)
        self._control_number_key = control_number_key
        self._charset = charset
        self._results_encoding = results_encoding

    def _make_connection(self):
        """
        Returns a connection to the Z39.50 server
        """
        # Create connection to database
        connection = zoom.Connection(
            self._host,
            self._port,
            charset = self._charset,
        )
        connection.databaseName = self._database
        connection.preferredRecordSyntax = self._syntax

        return connection

    def library_search(self, query):
        """
        @param query: The query to be performed
        @type query: molly.apps.library.models.LibrarySearchQuery
        @return: A list of results
        @rtype: [LibrarySearchResult]
        """

        connection = self._make_connection()

        # Convert Query object into a Z39.50 query - we escape for the query by
        # removing quotation marks
        z3950_query = []
        if query.author:
            z3950_query.append('(au="%s")' % query.author.replace('"', ''))
        if query.title:
            z3950_query.append('(ti="%s")' % query.title.replace('"', ''))
        if query.isbn:
            z3950_query.append('(isbn="%s")' % query.isbn.replace('"', ''))
        if query.issn:
            z3950_query.append('((1,8)="%s")' % query.issn.replace('"', ''))

        z3950_query = zoom.Query('CCL', 'and'.join(z3950_query))

        try:
            results = self.Results(connection.search(z3950_query),
                self._wrapper, self._results_encoding)
        except zoom.Bib1Err as e:
            # 31 = Resources exhausted - no results available
            if e.condition in (31,):
                return []
            else:
                raise LibrarySearchError(e.message)
        else:
            return results

    def control_number_search(self, control_number):
        """
        @param control_number: The unique ID of the item to be looked up
        @type control_number: str
        @return: The item with this control ID, or None if none can be found
        @rtype: LibrarySearchResult
        """

        # Escape input
        control_number = control_number.replace('"', '')

        z3950_query = zoom.Query(
            'CCL', '(1,%s)="%s"' % (self._control_number_key, control_number))
        connection = self._make_connection()
        results = self.Results(connection.search(z3950_query), self._wrapper,
            self._results_encoding)
        if len(results) > 0:
            return results[0]
        else:
            return None
