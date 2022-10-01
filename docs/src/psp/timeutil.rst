.. _timeutil:

==========================================
:mod:`timeutil` --- Time utility functions
==========================================

.. module:: psp.timeutil
   :synopsis: Time utility

.. testsetup::

   from psp.timeutil import *


.. TODO: Write an introduction


-------
Parsers
-------

.. function:: parse_timezone(s)

   Parse a fixed time zone string.

   Strings that match against the following regex, as well as ``UTC`` and
   ``GMT`` themselves, work in general:

   .. code-block:: text

      \A (?: UTC | GMT )?     # can be proceded with UTC or GMT
      (                       # group: time components
        [+-]                  #   sign
        \d{2} : \d{2}         #   hours and minutes
        (?:
          : \d{2}             #   seconds
          (?: \. \d{1,6} )?   #   microseconds
        )?
      )\Z

   Note that sign is a mandatory part of the string, so ``08:00`` and
   ``UTC08:00`` won't work.  And of course, even if the regex matches,
   don't expect something like ``+69:42`` or ``-11:69`` to work.  Offset
   also needs to be strictly between ``-timedelta(hours=24)`` and
   ``timedelta(hours=24)``, so ``+24:00`` wouldn't work either, even if
   it is a valid offset.

   Examples:

   .. doctest::

      >>> parse_timezone('-07:00')
      datetime.timezone(datetime.timedelta(days=-1, seconds=61200))
      >>> parse_timezone('UTC')
      datetime.timezone.utc
      >>> parse_timezone('GMT+08:00')
      datetime.timezone(datetime.timedelta(seconds=28800))
      >>> parse_timezone('sus')
      Traceback (most recent call last):
        ...
      ValueError: invalid time zone string: 'sus'

.. function:: parse_date(s)

   Parse a date string.  This calls |date_fif|.

.. function:: parse_datetime(s, tzinfo=None, fold=None)

   Parse a date time string.  This calls |datetime_fif| to get a base
   aware/naive date time to work on.  If the parsed date time has no
   *tzinfo* and *tzinfo* is provided (not *None*), the provided *tzinfo*
   will be used.  In addition, if *fold* is not *None*, the *fold*
   will be used too.

.. function:: parse_time(s, tzinfo=None, fold=None)

   Parse a time string.  This calls |time_fif| to get a base aware/naive
   time to work on.  If the parsed time has no *tzinfo* and *tzinfo* is
   provided (not None), the provided *tzinfo* will be used.  In addition,
   if *fold* is not None, the *fold* will be used too.

.. |date_fif| replace:: :meth:`date.fromisoformat() <datetime.date.fromisoformat>`
.. |time_fif| replace:: :meth:`time.fromisoformat() <datetime.time.fromisoformat>`
.. |datetime_fif| replace:: :meth:`datetime.fromisoformat() <datetime.datetime.fromisoformat>`


-----------------
String formatters
-----------------

.. function:: format_offset(off)

   Format a :class:`~datetime.timedelta` offset as returned by
   :meth:`~datetime.tzinfo.utcoffset`.

.. function:: format_date(d)

   Format a :class:`~datetime.date` object.

.. function:: format_time(dt)

   Format a :class:`~datetime.datetime` object and return a *str*
   suitable for the ``time`` entry-level attribute.

.. function:: format_datetime(dt)

   Format a :class:`~datetime.datetime` object and return a *str*
   suitable for the ``date-time`` entry-level attribute.


-------------
Miscellaneous
-------------

.. function:: is_naive(dt)

   Determine whether a datetime is naive.
   According to the `documentation`_, a datetime object *dt* is naive when:

   *  ``dt.tzinfo is None``; or
   *  ``dt.tzinfo.utcoffset(dt) is None``.

   .. _documentation: https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive

   The function returns True when any of the above criteria meets.
