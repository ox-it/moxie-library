import logging
import datetime
import urllib2
from lxml import etree

from PyZ3950 import zoom

logger = logging.getLogger(__name__)


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
        self._wrapper = USMARCSearchResult
        self._control_number_key = control_number_key
        self._charset = charset
        self._results_encoding = results_encoding

    def handles(self, doc):
        # TODO it has to change
        return True

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
        Search the library with a search query
        :param query: The query to be performed
        :type query: :py:class:`LibrarySearchQuery`
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
                self._wrapper, self._results_encoding)
        except zoom.Bib1Err as e:
            # 31 = Resources exhausted - no results available
            if e.condition in (31,):
                return []
            else:
                raise LibrarySearchException(e.message)
        else:
            return results

    def control_number_search(self, control_number):
        """
        Search the library with a unique ID of a resource
        :param control_number: The unique ID of the item to be looked up
        :type control_number: str
        :return The item with this control ID, or None if none can be found
        :rtype LibrarySearchResult
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



class LibrarySearchResult(object):
    """
    An object holding an individual result from a search
    """

    id = ''
    """
    @ivar id: A unique ID to reference this item in the database
    @type id: str
    """

    title = ''
    """
    @ivar title: The title of this book
    @type title: str
    """

    publisher = ''
    """
    @ivar publisher: The publisher of this book
    @type publisher: str
    """

    author = ''
    """
    @ivar author: The author(s) of this book
    @type author: str
    """

    description = ''
    """
    @ivar description: A description of this book
    @type description: str
    """

    edition = ''
    """
    @ivar edition: The edition of this book
    @type edition: str
    """

    copies = 0
    """
    @ivar copies: The number of copies of this book held
    @type copies: int
    """

    holding_libraries = 0
    """
    @ivar holding_libraries: The number of libraries which hold copies of this
                             book
    @type holding_libraries: int
    """

    isbns = []
    """
    @ivar isbns: The ISBNs associated with this item
    @type isbns: list of strings
    """

    issns = []
    """
    @ivar isbns: The ISSNs associated with this item
    @type isbns: list of strings
    """

    holdings = {}
    """
    @ivar holdings: A dictionary where library names are keys and the value is
                    a list of dictionaries, one for each copy of the item held.
                    This dictionary has the following keys: due (the due date),
                    availability (one of the AVAIL_ keys below),
                    availability_display (the display text for availability
                    status) and materials_specified (an additional value
                    typically indicating what issue of a copy this is)
    @type holdings: dict
    """

    AVAIL_UNAVAILABLE, AVAIL_UNKNOWN, AVAIL_STACK, AVAIL_REFERENCE,\
    AVAIL_AVAILABLE = range(5)

    def simplify_for_render(self):
        return {
            '_pk': self.id,
            'control_number': self.control_number,
            'title': self.title,
            'publisher': self.publisher,
            'author': self.author,
            'description': self.description,
            'edition': self.edition,
            'copies': self.copies,
            'holding_libraries': self.holding_libraries,
            'isbns': self.isbns,
            'issns': self.issns,
            #'holdings': self.libraries,
            }

    def __unicode__(self):
        return self.title


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
            self.metadata = marc_to_unicode(self.metadata)

        self.libraries = {}

        for datum in self.metadata[self.USM_LOCATION]:
            library = Library(datum['b'] + datum.get('c', []))

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

            # TODO watch how this dict is working
            if not library in self.libraries:
                self.libraries[library] = []
            self.libraries[library].append( {
                'due': due_date,
                'availability': availability,
                'availability_display': datum['y'][0] if 'y' in datum else None,
                'shelfmark': shelfmark,
                'materials_specified': materials_specified,
                } )

        for library in self.libraries:
            library.availability = max(l['availability'] for l in self.libraries[library])

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
        availability = False
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
        return
        xml = urllib2.urlopen("%s?op=circ-status&library=BIB01&sys_no=%s" % (self.aleph_url, self.control_number))
        et = etree.parse(xml)
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
                            #statsd.incr('library.availability.matchSuccess')
                            break
                    else:  # Doesn't run if we break, only when we run out of items
                        logger.info("Couldn't find match for location - %s" % location)
                        #statsd.incr('library.availability.matchFail')


class Library(object):
    """
    An object representing a library (used in holdings)

    @ivar location: an identifier for this library
    """

    def __init__(self, location):
        self.location = tuple(location)

    def __unicode__(self):
        return "/".join(self.location)
    __repr__ = __unicode__

    def __hash__(self):
        return hash((type(self), self.location))

    def __eq__(self, other):
        return self.location == other.location

    def get_entity(self):
        """
        Gets the entity for this library. This look up is done using the
        identifier namespace defined in the config. Returns None if no
        identifier can be found.
        """
        return None
        if hasattr(app_by_local_name('library'), 'library_identifier'):
            library_identifier = app_by_local_name('library').library_identifier
            try:
                return get_entity(library_identifier, '/'.join(self.location))
            except (Http404, Entity.MultipleObjectsReturned):
                return None
        else:
            return None

    def simplify_for_render(self, simplify_value, simplify_model):
        entity = self.get_entity()
        return {
            '_type': 'library.Library',
            'location_code': simplify_value(self.location),
            #'entity': simplify_value(entity),
            #'display_name': entity.title if entity else "/".join(self.location),
            }


class LibrarySearchQuery:
    """
    An object which gets passed to library search providers containing a library
    search query
    """

    STOP_WORDS = frozenset( (
        # Translators: A list of stop words to be filtered out during library searches
        "a,able,about,across,after,all,almost,also,am,among,an,and,any,are,as,at,be,because,been,but,by,can,cannot,could,dear,did,do,does,either,else,ever,every,for,from,get,got,had,has,have,he,her,hers,him,his,how,however,i,if,in,into,is,it,its,just,least,let,like,likely,may,me,might,most,must,my,neither,no,nor,not,of,off,often,on,only,or,other,our,own,rather,said,say,says,she,should,since,so,some,than,that,the,their,them,then,there,these,they,this,tis,to,too,twas,us,wants,was,we,were,what,when,where,which,while,who,whom,why,will,with,would,yet,you,your").split(',') )

    class InconsistentQuery(ValueError):
        def __init__(self, msg):
            self.msg = msg

    @staticmethod
    def _clean_isbn(isbn):
        """
        Tidy up ISBN input - limit to only allowed characters, replacing * with
        X
        """

        # Replace * with X
        isbn = isbn.replace('*', 'X')

        # Replace extroneous characters
        isbn = ''.join(c for c in isbn if (c in '0123456789X'))

        return isbn

    @staticmethod
    def _clean_input(input):
        """
        Remove stop words from the input

        @return: The cleaned string and a set of removed stop words
        @rtype: str, frozenset
        """

        # Cheap and nasty tokenisation
        cleaned = []
        removed = set()
        for word in input.split(' '):
            if word in LibrarySearchQuery.STOP_WORDS:
                removed.add(word)
            else:
                cleaned.append(word)
        return ' '.join(cleaned), frozenset(removed)

    def __init__(self, title=None, author=None, isbn=None, issn=None):
        """
        @param title: The title of the book to search for
        @type title: str or None
        @param author: The author of the book to search for
        @type author: str or None
        @param isbn: an ISBN number to search for - can contain * in place of X.
        @type isbn: str or None
        @param issn: an ISSN number to search for - can contain * in place of X.
        @type issn: str or None
        @raise LibrarySearchQuery.InconsistentQuery: If the query parameters are
            inconsistent (e.g., isbn specified alongside title and author, or no
            queries present)
        """

        if isbn and issn:
            raise self.InconsistentQuery(
                _("You cannot specify both an ISBN and an ISSN."))

        if (title or author) and (isbn or issn):
            raise self.InconsistentQuery(
                _("You cannot specify both an ISBN and a title or author."))

        if not (title or author or isbn or issn):
            raise self.InconsistentQuery(
                _("You must supply some subset of title or author, and ISBN."))

        self.removed = set()

        if title:
            self.title, removed = self._clean_input(title)
            self.removed |= removed
        else:
            self.title = None

        if author:
            self.author, removed = self._clean_input(author)
            self.removed |= removed
        else:
            self.author = None

        if isbn:
            self.isbn = self._clean_isbn(isbn)
        else:
            self.isbn = None

        if issn:
            self.issn = self._clean_isbn(issn)
        else:
            self.issn = None



class LibrarySearchException(Exception):

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return "Library search exception: {0}".format(self.message)