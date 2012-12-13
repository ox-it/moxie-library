import logging
import datetime
import requests
from lxml import etree
from collections import defaultdict

from PyZ3950 import zoom

from moxie_library.domain import LibrarySearchResult, LibrarySearchException

logger = logging.getLogger(__name__)


class Z3950(object):

    class Results:
        """
        A thing that pretends to be a list for lazy parsing of search results
        """

        def __init__(self, results, wrapper, results_encoding, availability=False, aleph_url=""):
            self.results = results
            self._wrapper = wrapper
            self._results_encoding = results_encoding
            self._availability = availability
            self._aleph_url = aleph_url

        def __iter__(self):
            for result in self.results:
                yield self._wrapper(result,
                    results_encoding=self._results_encoding,
                    availability=self._availability, aleph_url=self._aleph_url)

        def __len__(self):
            return len(self.results)

        def __getitem__(self, key):
            if isinstance(key, slice):
                if key.step:
                    raise NotImplementedError("Stepping not supported")
                return (self._wrapper(r, results_encoding=self._results_encoding, availability=self._availability, aleph_url=self._aleph_url)\
                    for r in self.results.__getslice__(key.start, key.stop))
            else:
                return self._wrapper(self.results[key],
                    results_encoding=self._results_encoding, availability=self._availability, aleph_url=self._aleph_url)

    def __init__(self, host, database, port=210, syntax='USMARC',
                 charset='UTF-8', control_number_key='12',
                 results_encoding='marc8', aleph_url=''):
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
        self._wrapper = OXMARCSearchResult
        self._control_number_key = control_number_key
        self._charset = charset
        self._results_encoding = results_encoding
        self._aleph_url = aleph_url

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

    def library_search(self, query, availability=False):
        """
        Search the library with a search query
        :param query: The query to be performed
        :type query: :py:class:`LibrarySearchQuery`
        :param availability: annotate with availability information
        :type availability: boolean
        :return A list of results
        :rtype [LibrarySearchResult]
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
                self._wrapper, self._results_encoding, availability=availability, aleph_url=self._aleph_url)
        except zoom.Bib1Err as e:
            # 31 = Resources exhausted - no results available
            if e.condition in (31,):
                return []
            else:
                raise LibrarySearchException(e.message)
        else:
            r = []
            for result in results:
                try:
                    r.append(result)
                except:
                    pass
            return r
        finally:
            connection.close()

    def control_number_search(self, control_number, availability=True):
        """
        Search the library with a unique ID of a resource
        :param control_number: The unique ID of the item to be looked up
        :type control_number: str
        :param availability: annotate with availability information
        :type availability: boolean
        :return The item with this control ID, or None if none can be found
        :rtype LibrarySearchResult
        """

        # Escape input
        control_number = control_number.replace('"', '')

        z3950_query = zoom.Query(
            'CCL', '(1,%s)="%s"' % (self._control_number_key, control_number))
        connection = self._make_connection()
        results = self.Results(connection.search(z3950_query), self._wrapper,
            self._results_encoding, availability=availability, aleph_url=self._aleph_url)
        if len(results) > 0:
            return results[0]
        else:
            return None


class SearchResult(LibrarySearchResult):

    AVAILABILITIES = {
        'Available': LibrarySearchResult.AVAIL_AVAILABLE,
        'Reference': LibrarySearchResult.AVAIL_REFERENCE,
        'Confined': LibrarySearchResult.AVAIL_REFERENCE,
        'Check shelf': LibrarySearchResult.AVAIL_UNKNOWN,
        'Please check shelf': LibrarySearchResult.AVAIL_UNKNOWN,
        'In place': LibrarySearchResult.AVAIL_STACK,
        'Missing': LibrarySearchResult.AVAIL_UNAVAILABLE,
        'Temporarily missing': LibrarySearchResult.AVAIL_UNAVAILABLE,
        'Reported Missing': LibrarySearchResult.AVAIL_UNAVAILABLE,
        'Withdrawn': LibrarySearchResult.AVAIL_UNAVAILABLE,
        '': LibrarySearchResult.AVAIL_UNKNOWN,
        }


class USMARCSearchResult(SearchResult):
    USM_CONTROL_NUMBER = 1
    USM_ISBN = 20
    USM_ISSN = 22
    USM_AUTHOR = 100
    USM_TITLE_STATEMENT = 245
    USM_EDITION = 250
    USM_PUBLICATION = 260
    USM_PHYSICAL_DESCRIPTION = 300
    USM_LOCATION = 852

    def __init__(self, result, results_encoding):
        self.str = str(result)
        self.metadata = {self.USM_LOCATION: []}

        items = self.str.split('\n')[1:]
        for item in items:
            heading, data = item.split(' ', 1)
            heading = int(heading)
            if heading == self.USM_CONTROL_NUMBER:
                self.control_number = data

            # We'll use a slice as data may not contain that many characters.
            # LCN 12110145 is an example where this would otherwise fail.
            if data[2:3] != '$':
                continue

            subfields = data[3:].split(' $')
            subfields = [(s[0], s[1:]) for s in subfields]

            if not heading in self.metadata:
                self.metadata[heading] = []

            m = {}
            for subfield_id, content in subfields:
                if not subfield_id in m:
                    m[subfield_id] = []
                m[subfield_id].append(content)
            self.metadata[heading].append(m)

        if results_encoding == 'marc8':
            #self.metadata = marc_to_unicode(self.metadata)
            pass

        self.libraries = defaultdict(dict)

        for datum in self.metadata[self.USM_LOCATION]:
            library_id = '/'.join(datum['b'] + datum.get('c', []))

            # Do not use availability information from this provider
            # TODO clean
            if False:
                # Availability
                if not 'p' in datum:
                    # Unknown availability
                    availability = LibrarySearchResult.AVAIL_UNKNOWN
                    datum['y'] = ['Check web OPAC']
                    due_date = None
                elif not 'y' in datum:
                    # Unknown availability
                    due_date = None
                    availability = LibrarySearchResult.AVAIL_UNKNOWN
                elif datum['y'][0].startswith('DUE BACK: '):
                    # To be available in due date
                    due_date = datetime.strptime(datum['y'][0][10:], '%d/%m/%y')
                    availability = LibrarySearchResult.AVAIL_UNAVAILABLE
                else:
                    # Unknown availability
                    due_date = None
                    availability = self.AVAILABILITIES.get(datum['y'][0],
                        LibrarySearchResult.AVAIL_UNAVAILABLE)

            # Shelfmarks
            if 'h' in datum:
                shelfmark = datum['h'][0]
                if 't' in datum:
                    shelfmark = "%s (copy %s)" % (shelfmark, datum['t'][0])
            elif 't' in datum:
                shelfmark = "Copy %s" % datum['t'][0]
            else:
                shelfmark = None

            materials_specified = datum['3'][0] if '3' in datum else None

            self.libraries[library_id] = defaultdict(list)

            self.libraries[library_id]['holdings'].append({
                #'due': due_date,
                #'availability': availability,
                #'availability_display': datum['y'][0] if 'y' in datum else None,
                'shelfmark': shelfmark,
                'materials_specified': materials_specified,
                })

        #for library in self.libraries:
        #    self.libraries[library]['availability'] = max(l['availability'] for l in self.libraries[library])

    def _metadata_property(heading, sep=' '):
        def f(self):
            if not heading in self.metadata:
                return None
            field = self.metadata[heading][0]
            return sep.join(' '.join(field[k]) for k in sorted(field))
        return property(f)

    title = _metadata_property(USM_TITLE_STATEMENT)
    publisher = _metadata_property(USM_PUBLICATION)
    author = _metadata_property(USM_AUTHOR)
    description = _metadata_property(USM_PHYSICAL_DESCRIPTION)
    edition = _metadata_property(USM_EDITION)
    copies = property(lambda self: len(self.metadata[self.USM_LOCATION]))
    holding_libraries = property(lambda self: len(self.libraries))

    @property
    def isbns(self):
        if self.USM_ISBN in self.metadata:
            return [a.get('a', ["%s (invalid)" % a.get('z', ['Unknown'])[0]])[0] for a in self.metadata[self.USM_ISBN]]
        else:
            return []

    @property
    def issns(self):
        if self.USM_ISSN in self.metadata:
            return [a['a'][0] for a in self.metadata[self.USM_ISSN]]
        else:
            return []


class OXMARCSearchResult(USMARCSearchResult):
    """Largely does the same as USMARCSearchResults but if availability=True then queries
    Aleph to get holdings data.
    """
    def __init__(self, *args, **kwargs):
        availability = kwargs.pop('availability')
        self.aleph_url = kwargs.pop('aleph_url')
        super(OXMARCSearchResult, self).__init__(*args, **kwargs)
        # Attach availability information to self.metadata
        if availability:
            self.annotate_availability()
            for library in self.libraries:
                library.availability = max(l['availability'] for l in self.libraries[library])

    def sanitize_shelfmark(self, shelfmark):
        """Reverts changes made by USMARCSearchResult.__init__ to shelfmarks.
        This seems the quickest/dirtiest way to get the job done.
        """
        if '(copy' in shelfmark:
            shelfmark = shelfmark[:shelfmark.index('(copy')]
        return shelfmark.strip()

    def annotate_availability(self):
        """Interesting for loop here, uses the for else.
        We go through all books in the libraries data (should only be 1 book per lib)
        Try to match the shelfmark from Z39.50 with Aleph and adds the availability info
        """
        response = requests.get("{base}?op=circ-status&library=BIB01&sys_no={id}".format(base=self.aleph_url, id=self.control_number),
                                    timeout=2)
        if response.ok:
            try:
                self.parse_availability(response.content)
            except Exception as e:
                logger.error('Unable to parse availability information', exc_info=True,
                    extra={'data': {'control_number': self.control_number}})
        else:
            logger.warning("Couldn't reach {url}, HTTP {code}".format(url=self.aleph_url,
                code=response.status_code), extra={'data': {'control_number': self.control_number}})

    def parse_availability(self, xml):
        et = etree.fromstring(xml, parser=etree.XMLParser(ns_clean=True, recover=True))
        items = et.xpath('/circ-status/item-data')
        found = set()
        for library, books in self.libraries.items():
            for book in books:
                if book['shelfmark']:
                    location = self.sanitize_shelfmark(book['shelfmark'])
                    for item in items:
                        if item in found:
                            continue
                        item_location = item.find('location').text
                        if item_location and item_location.startswith(location):
                            avail = item.find('due-date').text
                            try:
                                due_date = datetime.strptime(avail, '%d/%m/%y')
                                book['due'] = due_date
                                avail = "Due back: %s" % avail
                                availability = LibrarySearchResult.AVAIL_UNAVAILABLE
                            except:
                                availability = self.AVAILABILITIES.get(avail,
                                    LibrarySearchResult.AVAIL_UNAVAILABLE)
                            book['availability'] = availability
                            if avail[-1] == '*':
                                book['availability_display'] = "Closed Stack / Request via SOLO"
                                book['availability'] = LibrarySearchResult.AVAIL_STACK
                            else:
                                book['availability_display'] = avail
                            found.add(item)
                            break
                    else:  # Doesn't run if we break, only when we run out of items
                        logger.info("Couldn't find match for location - %s" % location)