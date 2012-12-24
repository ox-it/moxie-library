Library endpoint
================

Endpoint to search and retrieve information about media in libraries. Follows specification of Moxie.

.. http:get:: /library/item:(string:id)

    Get details of a media by its ID

    **Example request**:

    .. sourcecode:: http

		GET /library/item:015044225 HTTP/1.1
		Host: api.m.ox.ac.uk
		Accept: application/json

    **Example response as JSON**:

    .. sourcecode:: http

		HTTP/1.1 200 OK
		Content-Type: application/json

        {
          "publisher": "[Paris] : Minist\u00e8re de la Reconstruction et de l'Urbanisme, 1951.",
          "description": "2 maps.",
          "author": null,
          "holdings": {
            "BODBL": {
              "holdings": [
                {
                  "materials_specified": null,
                  "shelfmark": "C21:50 Arreau (1)"
                }
              ]
            }
          },
          "control_number": "015044225",
          "copies": 1,
          "edition": null,
          "isbns": [],
          "title": "Arreau. [map]",
          "issns": []
        }

    :param id: ID of the resource
    :type id: string
    :param availability: true if media should be annotated with real-time availability (defaults to true)
    :type availability: boolean

    :statuscode 200: resource found
    :statuscode 404: no resource found

.. http:get:: /library/search

    Search for media by title and/or author or ISBN.

    **Example request**:

    .. sourcecode:: http

		GET /library/search?title=python HTTP/1.1
		Host: api.m.ox.ac.uk
		Accept: application/hal+json

    **Example response as HAL+JSON**:

    .. sourcecode:: http

		HTTP/1.1 200 OK
		Content-Type: application/hal+json

        {
            "_embedded": {
                "items": [
              {
                "description": "[96] p. of music : ill. ; 28 cm.", 
                "edition": null, 
                "id": "012192991", 
                "publisher": "London : Methuen, 1995.", 
                "_embedded": {
                  "BODBL": {
                    "website": "http://www.bodleian.ox.ac.uk/bodley", 
                    "phone": "", 
                    "address": "", 
                    "lat": "51.754105", 
                    "id": "oxpoints:32320008", 
                    "distance": 0, 
                    "name": "Bodleian Library", 
                    "opening_hours": "", 
                    "type_name": [
                      "Library"
                    ], 
                    "lon": "-1.254023", 
                    "_links": {
                      "self": {
                        "href": "/places/oxpoints:32320008"
                      }, 
                      "parent": {
                        "href": "/places/oxpoints:23233598", 
                        "title": "Bodleian Libraries"
                      }, 
                      "child": [
                        {
                          "href": "/places/oxpoints:32330056", 
                          "title": "Bodleian - Lower Camera Open Shelves"
                        }, 
                        [...]
                        {
                          "href": "/places/oxpoints:32330052", 
                          "title": "English Accessions"
                        }
                      ]
                    }, 
                    "type": [
                      "/university/library"
                    ]
                  }
                }, 
                "title": "The fairly incomplete & rather badly illustrated Monty Python song book / foreword by Elvis Presley ; middleword by God ; afterword by Brigadier N.Q.T.F. Sixpence ; [illustrated by Terry Gilliam, Gary Marsh, John Hurst ; music edited by John Du Prez].", 
                "holdings": {
                  "BODBL": [
                    {
                      "materials_specified": null, 
                      "shelfmark": "Mus. 5 d.1127"
                    }
                  ]
                }, 
                "author": null, 
                "copies": 1, 
                "_links": {
                  "self": {
                    "href": "/library/item:012192991/"
                  }
                }, 
                "isbns": [
                  "0749319526 (pbk)"
                ], 
                "issns": []
              }
            ]
          }, 
          "isbn": null, 
          "author": null, 
          "_links": {
            "hl:first": {
              "href": "/library/search?count=35&title=python"
            }, 
            "curie": {
              "href": "http://moxie.readthedocs.org/en/latest/http_api/relations.html#{rel}", 
              "name": "hl", 
              "templated": true
            }, 
            "self": {
              "href": "/library/search?title=python"
            }, 
            "hl:next": {
              "href": "/library/search?count=35&start=35&title=python"
            }, 
            "hl:last": {
              "href": "/library/search?count=35&start=153&title=python"
            }
          }, 
          "title": "python", 
          "size": 188
        }

    The response contains a list of results, links to go to first, previous, next and last pages depending on current `start` and `count` parameters, and the total count of results.

    :query title: title to search for
    :type title: string
    :query author: author to search for
    :type author: string
    :query isbn: isbn to search for
    :type isbn: isbn
    :query availability: true if search results should be annotated with real-time availability (defaults to false)
    :type availability: boolean
    :query start: first result to display
    :type start: int
    :query count: number of results to display
    :type count: int

    :statuscode 200: results found
    :statuscode 400: search query is inconsistent (expect details about the error as plain/text in the body of the response)
    :statuscode 500: search service is not available
