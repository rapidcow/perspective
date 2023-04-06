.. _backup_spec:

=============================
``backup.json`` Specification
=============================

:Author: rapidcow
:Date: Nov 29, 2021 (still WIP tho)

.. .. contents::
..    :local:
..    :depth: 1

--------
Abstract
--------

This is meant to provide a technical specification for the minimal
syntax of ``backup.json``, as read and written by
:mod:`psp.serializers.json`.

.. important::

   This isn't complete at the moment, so please refer to "Backup File
   Structure" section from :ref:`basicproc` for a more detailed explanation!

-----------
Terminology
-----------

Here are some terms that will be used.

attribute
   An attribute is a pair of name and value, similar to key and value of a
   Python *dict*.  For example the ``tz`` attribute (or more verbosely, the
   value of the attribute with the name ``tz``) is a string and the ``data``
   attribute of entries may be a *str* or *bool*.  To make it consistent
   I will use code literals for attribute names (like ``tz`` and ``data``)
   and italic for variables types (like *dict* and *str*) and names (like
   *panels* and *entries*).

field
   Another name for attribute (sometimes).

*dict*, *list*, *str*, *bool*, null
   These will be convenient Pythonic terms to refer to JSON objects,
   arrays, strings, and booleans.  They are used mainly because object
   means something different in Python; the use of null, however, is
   preserved, despite in Python it is the singleton ``None``.

*text*
   When an attribute is a *text* attribute, it must be either a *str*
   or a *list* of *str* (such that ``''.join()`` can create a string from it).

Other terms such as "panel" and "entry" will be explained progressively
in the following text.


--------------------
Top-Level Attributes
--------------------

A backup file is always a *dict*, inside which are what we will call the
*top-level attributes* and a *list* of *panels* stored under the key
``data``.  Here we will enumerate several keys (all surprisingly optional)
that you may use.

tz (optional)
   A *str* representing the time zone for everything in this backup.
   Must be valid when passed to |parse_timezone|.
   This is optional but a time zone must be eventually provided as
   |JSONLoader| parses some time/date time string.

paths (optional)
   A *list* of *str* for the lookup paths.  Each time the ``input``
   attribute of an *entry* is parsed, its value is prepended with the
   ``base_dir`` option of |JSONLoader| and a path in this attribute.

   By default this evaluates to simply ``['.']``---that is, the same
   directory as ``base_dir``.  If this is not omitted, however, be noted
   that ``"."`` will not be automatically added and you have to
   explicitly add it if you want |JSONLoader| to look in the same
   directory as ``base_dir``.

data (optional)
   A *list* of *dict*, each *dict* being what is called a *panel*.  The
   content of each *dict* is elaborated in the following section.
   An empty list is assumed if this is omitted.

Any other key is ignored by |JSONLoader|, though there is one key that is
recommended for you to use.  It is also addressed because |JSONDumper|
exports it and the ``psp synopsis`` command recognizes it.

desc (optional)
   A *text* attribute giving a brief description of this backup file.
   This is just a recommendation previously reinforced by
   :mod:`basicproc` and, sometimes, other "nonstandard" parts of
   my code.  |JSONLoader| never tries to parse this.


------
Panels
------

Now for the panels!  A *panel* is a container of *entries*, loosely speaking.
It does cooler stuff than that though, but first let's talk about the one and
only **required** attribute:

date
   A *str* representing the date of the panel.  Must be valid when
   passed to |parse_date|.

For providing entries:

entries (optional)
   A *list* of *dict*, each *dict* being what is called an *entry*.
   The content of each *dict* is elaborated in the following section.
   An empty list is assumed if this is omitted.

There is only one valid optional attribute:

rating (optional)
   A *str* representing the rating of the panel (can be null).
   The three ratings from Perspective from bad to good are
   represented with the strings ``":("``, ``":|"``, and ``":)"``.
   (I did not use numbers because I'm not a nerd >_> (well, not entirely))

   Rating is set to null when omitted.

   Example:

   .. doctest::

      >>> from psp.serializers.json import load_json
      >>> from io import StringIO
      >>> panels = load_json(StringIO("""\
      ... {
      ...   "data": [
      ...     {
      ...       "date": "2021-04-29",
      ...       "rating": ":)"
      ...     },
      ...     {
      ...       "date": "2021-12-25",
      ...       "rating": null
      ...     },
      ...     {
      ...       "date": "2022-06-01"
      ...     }
      ...   ]
      ... }
      ... """))
      >>> for panel in panels:
      ...     rating = panel.get_attribute('rating', default=None)
      ...     print('{!r:27}  {!r}'.format(panel.date, rating))
      datetime.date(2021, 4, 29)   ':)'
      datetime.date(2021, 12, 25)  None
      datetime.date(2022, 6, 1)    None


-------
Entries
-------

Now for the entries... this can get tricky since this is where most of the
things take place.

.. TODO talk about required arguments, then optional


---------
Inference
---------

.. TODO talk about the logic behind inference

This will be a reorganized version of the algorithm from
:ref:`basicproc <basicproc_inference>`.


.. |JSONLoader| replace:: :class:`~psp.serializers.json.JSONLoader`
.. |JSONDumper| replace:: :class:`~psp.serializers.json.JSONDumper`
.. |parse_timezone| replace:: :meth:`JSONLoader.parse_timezone() <psp.serializers.json.JSONLoader.parse_timezone>`
.. |parse_date| replace:: :meth:`JSONLoader.parse_date() <psp.serializers.json.JSONLoader.parse_date>`
