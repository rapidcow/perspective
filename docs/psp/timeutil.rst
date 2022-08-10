.. _timeutil:

==========================================
:mod:`timeutil` --- Time utility functions
==========================================

.. module:: psp.timeutil
   :synopsis: Time utility

.. testsetup::

   from psp.timeutil import (parse_timezone, parse_datetime, parse_date,
       parse_time, is_naive, format_offset)


.. XXX: hasn't been tested a lot

.. function:: parse_timezone(s)

   Parse a time zone string such as ``+08:00`` and ``-07:00``.

   Strings that match against the following regex that are guaranteed to
   work:

   .. code-block:: text

      \A (?: UTC | GMT )?     # can be proceded with UTC or GMT
      ([+-])?                 # group 1: optional sign
      (                       # group 2: time component
        \d{2} : \d{2}         #   hours and minutes
        (?:
          : \d{2}             #   seconds
          (?: \. \d{1,6} )?   #   microseconds
        )?
      )\Z

   In addition, for Python 3.9 and above, if ``tzdata`` is installed, the
   string will be passed to ``zoneinfo.ZoneInfo()`` to create a ``ZoneInfo``
   object.

   .. TODO: This example will not run if sys.version_info < (3.9) or
   .. tzdata isn't installed... so make it an optional test somehow :/

   Examples:

   .. doctest::

      >>> parse_timezone('-07:00')
      datetime.timezone(datetime.timedelta(days=-1, seconds=61200))
      >>> parse_timezone('America/Los_Angeles')
      zoneinfo.ZoneInfo(key='America/Los_Angeles')

.. function:: parse_datetime(s, tzinfo=None, fold=None)

   Parse a date time string.  If the parsed date time has no ``tzinfo``
   and ``tzinfo`` is provided (not ``None``), the provided ``tzinfo`` will
   be used.  In addition, if ``fold`` is not ``None``, the ``fold`` will be
   used too.

.. function:: parse_date(s)

   Parse a date string.  ISO strings of the form ``YYYY-MM-DD`` are always
   valid as they are passed to |fromisoformat|_.  If that fails, a list of
   formats :attr:`DATE_FORMATS` are tried before a ``ValueError`` is raised.

.. Nested inline markup is not a thing in reStructuredText O-O
   https://docutils.sourceforge.io/FAQ.html#is-nested-inline-markup-possible

.. |fromisoformat| replace:: ``datetime.date.fromisoformat()``
.. _fromisoformat: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat


-----------------
Global Attributes
-----------------

Don't punch me for doing this okay...?  I know I'm not supposed to do this...
but hey, you are probably not supposed to change this either?  I made it so
that you can subclass :class:`JSONLoader` and override the methods, y'know...

.. attribute:: DATE_FORMATS

   The constant that defines the list of date formats to try::

      DATE_FORMATS = [
          '%b %d %Y', '%b %d, %Y', '%B %d %Y', '%B %d, %Y',
          '%a %b %d %Y', '%a, %b %d, %Y', '%A %B %d %Y', '%A, %B %d, %Y',
          '%d %b %Y', '%d %b, %Y', '%d %B %Y', '%d %B, %Y',
          '%a %d %b %Y', '%a, %d %b, %Y', '%A %d %B %Y', '%A, %d %B, %Y',
          '%m/%d/%y', '%m/%d/%Y',
      ]
