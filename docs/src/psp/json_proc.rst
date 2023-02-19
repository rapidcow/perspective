.. _processors_json:

================================================================
:mod:`processors.json_processor` --- JSON backup file processors
================================================================

.. module:: psp.processors.json_processor
   :synopsis: JSON backup file processors

Some of the classes and functions are imported into the :mod:`processors`
module.  Specifically::

   from psp.processors import load_json, dump_json
   from psp.processors import JSONLoader, JSONDumper

can be used instead of the whole long name.

All the examples below will use the following import::

   from psp.processors.json_processor import *

.. important::

   This module deals with what are called *backup files*, which are
   JSON files following a format described in :ref:`backup_spec`.
   Make sure to refer to that because the default implementation here
   is entirely based off of the rules described there!

.. testsetup::

   from psp.processors.json_processor import *


-----------
An Overview
-----------

The loading and dumping processes are unironically similar to, or even
dare I say entirely inspired by, :func:`json.load()` and :func:`json.dump()`.
The biggest difference being that instead of just loading from a file into
a Python *dict*, we process it and return a stream of
|Panel| objects.  Similarly, instead of taking a
Python object and dumping it to a file, we accept a stream of
|Panel| objects, convert them back to panel
*dict*\ s, and dump it to a file.  These operations are, at the highest
level, publicly exposed as the :meth:`JSONLoader.load` and
:meth:`JSONDumper.dump` methods, though in case you don't want too much
nuances then we also have :func:`load_json` and :func:`dump_json`, for
convenience, and only convenience, really.  (I was glad to learn the other
day that the :mod:`json` module called its counterparts
:class:`~json.JSONDecoder` and :class:`~json.JSONEncoder`, so... that's a
relief for me now that I'm not confusing anyone here!)

Okay, but seriously, I might write a longer overview here in the future.
But right now, just use the examples I gave elsewhere please...


-------
Loading
-------

Usually you want to use a loader like this::

   loader = JSONLoader()
   loader.configure(base_dir='path/to')
   with open('path/to/backup.json', encoding='utf-8'):
       panels = loader.load(fp)

But, well, ``base_dir`` totally depends on where you store external files
that ``input`` paths refer to.  Sometimes you might skip this as long as
you're fine with the default value (being the current working directory).

Now take heed of my words... **always use an encoding**.  I learned it the
hard way, but not providing an encoding could lead to issues since not
every computer in this world has UTF-8 as its default.  This is also why I
made it so that :meth:`JSONLoader.load` only takes a file object,
otherwise things will get clustered and we're making the method perform
two things (opening a file and processing).

.. And I don't really know much else to add

.. exception:: LoadError

   Error that occured while dumping a JSON file; subclass of
   :class:`ValueError`.

.. exception:: LoadWarning

   Warning that occured while dumping a JSON file.

.. class:: JSONLoader(**options)

   The JSON backup file loader class.  This class inherits from
   :class:`~psp.types.Configurable`, so you can technically use all the
   methods there, although we will stick to the |Configurable.configure|
   method in all the following examples since that has stuck around for a
   while.

   The constructor takes no positional arguments, and all keyword
   arguments are passed to the :meth:`configure` method.

   .. method:: configure(**options)

      Configure options.
      This is inherited from :class:`~psp.types.Configurable`.

      The following is a table of all options.

      +----------------------------+---------------------------+----------------------+-----------+
      | Option                     | Description               | Type                 | Default   |
      +============================+===========================+======================+===========+
      | ``base_dir``               | Base directory for        | *str* or             | ``None``  |
      |                            | *input* paths. (1)        | :class:`os.PathLike` |           |
      |                            |                           | or None              |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``json_options``           | Keyword arguments to      | *dict*               | ``{}``    |
      |                            | pass to ``json.loads()``. |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``check_panel_order``      | If true, warn on          | *bool*               | ``True``  |
      |                            | panel dates that are      |                      |           |
      |                            | not strictly              |                      |           |
      |                            | increasing. (2)           |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``check_entry_order``      | If true, warn on          | *bool*               | ``True``  |
      |                            | entry times that are      |                      |           |
      |                            | not increasing. (3)       |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``suppress_warnings``      | If true, all              | *bool*               | ``False`` |
      |                            | :exc:`LoadWarning`        |                      |           |
      |                            | is suppressed.            |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``error_on_warning``       | If true, all              | *bool*               | ``False`` |
      |                            | :exc:`LoadWarning`        |                      |           |
      |                            | is raised as              |                      |           |
      |                            | exceptions. (4)           |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``warn_ambiguous_paths``   | If true, warn for         | *bool*               | ``True``  |
      |                            | paths are found more      |                      |           |
      |                            | than once.                |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``data_decoders``          | Mapping for decoders of   | *dict*               | \(4)      |
      |                            | ``data-decoding``.        |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+

      Notes:

      (1)
         When ``base_dir`` is None, the loader raises :class:`LoadError`
         as soon as encountering the entry-level attribute ``input``.
         ``base_dir`` may be a relative path.

      (2)
         A warning is issued if ``d1 >= d2`` for any two consecutive panels
         of dates ``d1`` and ``d2``.

      (3)
         A warning is issued if ``t1 > t2`` for any two consecutive entries
         of times ``t1 and t2`` (converted to UTC).  In particular, main
         entries and insight entries (entries whose :attr:`insight` attribute
         is False and True respectively) should be ordered *separately*
         according to the above rule: either all insight entries follow main
         entries, or all main entries follow insight entries.  But if a
         transition from insight to main or vice versa occurred more than
         once, then a warning is issued.

      (4)
         This has no effect if ``suppress_warnings`` is true.

      (5)
         Default value is set to::

            {
                'base16': base64.b16decode,
                'base32': base64.b32decode,
                'base64': base64.b64decode,
                'base64_url': base64.urlsafe_b64decode,
                'ascii85': base64.a85decode,
                'base85': base64.b85decode,
            }

      More on the usage of these options in the
      :ref:`Options <json_loader_options>` section.

   There are two high-level methods used to load an archive: the
   :meth:`load` method directly loads from a file, and the :meth:`load_data`
   method loads from a *dict*.  Note that :meth:`load` ultimately calls
   :meth:`load_data`, so oftentimes overriding :meth:`load_data` is
   enough.

   .. method:: load(fp)

      Load an archive from *file*.  The content of the archive is read
      as a *dict* and then passed onto :meth:`load_data` with the *date*
      argument.

      Here's the definition of :meth:`load`, precisely::

          def load(self, fp):
              data = self.load_json(fp)
              return self.load_data(data)

      :param fp: A file-like object that implements a ``read()`` method.
      :returns: A generator from :meth:`load_data`.

   .. method:: load_json(fp)

      Load a JSON archive from a file object and return a *dict*.
      The *fp* argument is the same as that from :meth:`load`.

   .. method:: load_data(data)

      Load an archive from a *dict*, returning a list of panels if
      *date* is not given or a single panel if *date* is given.
      :meth:`load` calls this method.

      :param dict data: The JSON archive.
      :return: A *generator* that yields |Panel| objects from the JSON
               archive, until there is none left.
      :raises LoadError:
         Missing attribute (like not providing ``date``) or conflicting
         attributes (such as ``data`` and ``input``)
      :raises LoadWarning:
         Non-fatal issues (such as extraneous panel/entry attributes or
         finding more than one path for ``input``); only raised when
         ``error_on_warning`` is True
      :raises TypeError:
         Type mismatch (like providing an *int* for ``date``)
      :raises ValueError:
         Invalid value for time zone, date, datetime, time, etc.

      .. XXX: are parse_*() the only way ValueError could be raised??

      .. warning::

         As of version 0.2, :meth:`load` and :meth:`load_data` return a
         *generator*, not a fully loaded *list*.  This can get a bit risky
         considering the state may change while you're loading.  For example
         (slightly modified from my lazy code to be more practical for more
         you well-witted coders) if you overrode :meth:`load_data` like so::

            def load_data(self, *args, **kwargs):
                # set up something
                try:
                    return super().load_data(*args, **kwargs)
                finally:
                    # clean up something

         then when you try to use the generator, the cleanup code has
         already run and that is a problem.  But actually there is an easy
         way to solve it!  Instead of writing ``return``, you can
         ``yield from`` the other generator so the code waits before it
         runs the cleanup code.

         Still, look out instances where the state *could* be changed::

            loader = JSONLoader()
            with open(...) as fp:
                panels = loader.load(fp)
                next(panels)
                loader.configure(base_dir=something_else)
                next(panels)     # the option is changed here!

      :example:

      >>> data = {
      ...     'data': [
      ...         { 'date': '2022-02-22' },
      ...         { 'date': '2022-03-14' },
      ...     ]
      ... }
      >>> list(JSONLoader().load_data(data))
      [<Panel object on 2022-02-22>, <Panel object on 2022-03-14>]

   You shouldn't need more than these three methods to enjoy everything
   this class has to offer, but if you care about more customization,
   allow me to first explain how :meth:`load_data` works...

   Inside :meth:`load_data`, the loader splits *data* into two parts:
   the *panels* and the *attrs*.  *panels* is a list of *dict*\ s obtained
   from the ``data`` key, and *attrs* is everything else.  This splitting
   process is implemented in the :meth:`split_data` method.

   .. method:: split_data(data)

      Split the data and returns a tuple of ``(panels, attrs)``, the former
      being a list under the `panel` key and the latter being a *dict*
      constructed keys other than `panel`.  If *data* doesn't have
      ``panels``, *panels* is returned as ``[]``.

      The two attributes :meth:`split_data` guarantees to be set in
      *attrs* are the ``tz`` and ``paths`` attributes.  Validation is
      performed on them if they were present in *data* before splitting
      according to the following rules:

      *  ``tz`` must be a *str*, otherwise defaults to None
      *  ``paths`` must be a *list* of *str*, otherwise defaults to ``[.]``

   For each panel in the *panels* list, :meth:`load_data` calls
   :meth:`process_panel` with a shallow copy of the panel (as a *dict*)
   and a reference to *attrs* (**not a copy**).  It first creates a |Panel|
   object with no entries attached to it, then for each entry in
   the *entries* list, it calls :meth:`process_entry` with the newly created
   panel object, a shallow copy of the entry (as a *dict*) and a reference
   to *attrs* (again, not a copy), which returns an |Entry| object.  Each
   entry object is added to the panel with :meth:`Panel.add_entry()
   <psp.types.Panel.add_entry>` and finally the panel object is returned
   by :meth:`process_panel` and yielded by :meth:`load_data`.

   Very windy, I know, right?  Well I probably could have phrased it better,
   but essentially :meth:`load_data` calls :meth:`process_panel` to get
   every panel, and :meth:`process_panel` calls :meth:`process_entry` to get
   every entry.  The chained relations here are what's most important for you
   to understand here.

   .. method:: process_panel(panel, attrs)

      Process a JSON object representing a panel.

      :param dict panel: A shallow copy of the panel *dict* to be processed.
      :param dict attrs: Top-level attributes, as described above.
      :returns: A |Panel| object, always.

      .. note::

         In some cases, :meth:`process_panel` makes a copy of *attrs*
         before passing onto :meth:`process_entry`: when an attribute is
         overridden, to be exact.  Currently the only possibility is
         when the ``tz`` attribute is provided at panel-level.
         In any case, don't rely on the fact that *attrs* is passed as
         a direct reference and only *sometimes* copied.

   .. method:: process_entry(panel, entry, attrs)

      Process a JSON object representing an entry.

      :param panel: The panel this entry belongs to.
      :type panel: |Panel|
      :param dict entry: A shallow copy of the entry *dict* to be processed.
      :param dict attrs: Top-level attributes, as described above.
      :returns: An |Entry| object, always.

   .. note::

      Since *attrs* is passed as a reference, :meth:`process_panel`
      copies it, but only when a top-level attribute is being
      overridden locally (specifically, when ``tz`` is provided as a
      panel-level attribute).  Expect the same reference to be passed to
      :meth:`process_entry` when no top-level attribute is provided at
      panel-level.

      This feature, however, is *not* meant for you to mutate the
      attribute outside the panel/entry scope in a way it changes the
      entire loading process.  Technically I should make a copy for every
      panel and every entry to limit the scope, but I didn't do so to
      prevent redundant copying.  Just remember that if you're overriding
      :meth:`process_panel` or :meth:`process_entry` and you want to
      *mutate* something in *attrs* (not just *accessing*, but adding or
      removing or re-assigning certain attributes), **always make a
      shallow copy**, or you're probably writing inconsistent code.

   The following methods are responsible for parsing time-related things.
   Default implementation calls their corresponding functions in
   :mod:`timeutil <psp.timeutil>`.

   .. method:: parse_timezone(s)

      Parses the ``tz`` field, both at top-level and inside an entry.
      This calls
      :func:`timeutil.parse_timezone() <psp.timeutil.parse_timezone>`.

   .. method:: parse_date(s)

      Parses the ``date`` field, both in panel and in entry.  This calls
      :func:`timeutil.parse_date() <psp.timeutil.parse_date>`.

   Although the next two methods can be called as positional or keyword
   arguments, it is recommended to use keyword arguments as I'm not sure
   whether there will be more in the future...

   .. method:: parse_datetime(s, tzinfo, fold)

      Parses the ``date-time`` field in entry.  *tzinfo* and *fold* are
      ``None`` unless they are known.  This calls
      :func:`timeutil.parse_datetime() <psp.timeutil.parse_datetime>`.

   .. method:: parse_time(s, tzinfo, fold)

      Parses the ``time`` field in entry.  *tzinfo* and *fold* are
      ``None`` unless they are known.  This calls
      :func:`timeutil.parse_time() <psp.timeutil.parse_time>`.


.. _json_loader_options:

Loader Options
^^^^^^^^^^^^^^

``base_dir`` (loader)
'''''''''''''''''''''

One option you should always set when working with external ``input``
files is ``base_dir``, which determines the base directory all relative
``input`` paths start from.  The default value is the current working
directory, which may vary depending on where you run your interpreter.
Typically when you are loading from a file path stored under a variable
named ``file``, you might want to write something like this::

   # loader = JSONLoader()
   loader.configure(base_dir=os.path.dirname(file))
   panels = loader.load(file)


``error_on_warning`` + ``suppress_warning``
'''''''''''''''''''''''''''''''''''''''''''

Typically, a warning is issued in place of an error if the problem
encountered by the loader isn't detrimental to the output, like this
(warning message truncated):

.. disabling doctest on the warnings line since while the warning
   is printed to stderr and not stdout, but because of that we have
   to load the panels ahead of time... >_>

.. testsetup:: error_on_warning

      # XXX: Why do we have to do this?
      from psp.processors.json_processor import JSONLoader
      data = {'data': [{
         'date': '2022-02-22',
         'entries': [{'time': '08:00+00:00',
                      'data': 'text',
                      'invalid-key': 0}]
      }]}
      panels = list(JSONLoader(suppress_warnings=True).load_data(data))

.. doctest:: error_on_warning

   >>> data = {
   ...     'data': [
   ...         {
   ...             'date': '2022-02-22',
   ...             'entries': [
   ...                 {
   ...                     'time': '08:00+00:00',
   ...                     'data': 'text',
   ...                     'invalid-key': 0
   ...                 }
   ...             ]
   ...         }
   ...     ]
   ... }
   >>> panels = list(JSONLoader().load_data(data))# doctest: +SKIP
   psp/processors/json_processor.py:761: LoadWarning: ignored entry key: invalid-key
   >>> panels
   [<Panel object on 2022-02-22>]

To make debugging easier you can turn on the ``error_on_warning`` option
as it prints a useful stack trace that can help locate the problem:

.. doctest:: error_on_warning

   >>> list(JSONLoader(error_on_warning=True).load_data(data))
   Traceback (most recent call last):
     ...
   psp.processors.json_processor.LoadWarning: ignored entry key: invalid-key

On the other hand, if you want all warnings to be ignored, set the
``suppress_warning`` option to True.  This always overrides
``error_on_warning`` regardless of its value.


``check_panel_order``
'''''''''''''''''''''

The ``check_panel_order`` option is True by default in order to more
easily pick up wrong dates that is helpful for backing up entries by
hand:

>>> list(JSONLoader(error_on_warning=True).load_data({
...    'data': [{ 'date': '2019-06-01' },
...             { 'date': '2022-06-02' },
...             { 'date': '2019-06-03' }]
... }))
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: panel #2 (2022-06-02) is after panel #3 (2019-06-03)
>>> list(JSONLoader(error_on_warning=True).load_data({
...    'data': [{ 'date': '2022-02-02' },
...             { 'date': '2022-02-02' }]
... }))
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: panel #1 has the same date as #2 (2022-02-02)


``check_entry_order``
'''''''''''''''''''''

The ``check_entry_order`` option is True by default for a similar purpose
as ``check_panel_order``, except entries only have to be increasing and may
have equal time (with time zone taken into account, that is):

>>> data = {
...     'data': [
...         {
...             'date': '2021-07-25',
...             'entries': [
...                 { 'time': '03:14-07:00', 'data': '' }, # 10:14 UTC
...                 { 'time': '18:14+08:00', 'data': '' }, # 10:14 UTC
...                 { 'time': '10:15+00:00', 'data': '' }, # 10:15 UTC
...             ]
...         },
...         {
...             'date': '2021-07-27',
...             'entries': [
...                 { 'time': '03:14-07:00', 'data': '' }, # 10:14 UTC
...                 { 'time': '18:13+08:00', 'data': '' }, # 10:13 UTC
...             ]
...         }
...     ]
... }
>>> list(JSONLoader(error_on_warning=True).load_data(data))
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: inconsistent order in main entries in panel 2 on 2021-07-27 (entry 2 precedes entry 1 in time)

Note that when stepping through the generator, only the panel being yielded
is checked for:

>>> panel_iter = JSONLoader(error_on_warning=True).load_data(data)
>>> next(panel_iter)
<Panel object on 2021-07-25>
>>> next(panel_iter)
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: inconsistent order in main entries in panel 2 on 2021-07-27 (entry 2 precedes entry 1 in time)

Aside from the time being in increasing order, main entries (not insights)
must always come before insight entries, if there are any at all.
Within the main and insight entries, an increasing order must be
maintained, completely analogous to the example I gave above.  Below are
an example of good entry order and two examples of bad entry order:

>>> data = {
...     'tz': 'UTC',
...     'data': [
...         {
...             'date': '2021-08-17',
...             'entries': [
...                 { 'time': '00:00', 'data': '' },
...                 { 'date-time': '2021-11-20 15:00', 'data': '' },
...                 # Insight entries follow always main entries
...                 { 'date-time': '2021-08-21 11:00',
...                   'insight': True, 'data': '' },
...                 { 'date-time': '2022-01-01 03:00',
...                   'insight': True, 'data': '' }
...             ]
...         },
...         {
...             'date': '2021-08-18',
...             'entries': [
...                 { 'time': '21:00', 'data': '' },
...                 { 'date-time': '2021-08-29 11:00',
...                   'insight': True, 'data': '' },
...                 # This should be an insight
...                 # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
...                 { 'date-time': '2021-08-29 12:00', 'data': '' }
...             ]
...         }
...     ]
... }
>>> panel_iter = JSONLoader(error_on_warning=True).load_data(data)
>>> next(panel_iter)
<Panel object on 2021-08-17>
>>> next(panel_iter)
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: expected entry 3 to be an insight entry, got a main entry (in panel 2 on 2021-08-18)
>>> data = {
...     'tz': 'UTC',
...     'data': [
...         {
...             'date': '2021-08-19',
...             'entries': [
...                 { 'time': '18:00', 'data': '' },
...                 { 'date-time': '2022-08-29 11:00',
...                   'insight': True, 'data': '' },
...                 # This precedes the previous insight entry
...                 # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
...                 { 'date-time': '2021-08-29 12:00',
...                   'insight': True, 'data': '' }
...             ]
...         }
...     ]
... }
>>> next(JSONLoader(error_on_warning=True).load_data(data))
Traceback (most recent call last):
  ...
psp.processors.json_processor.LoadWarning: inconsistent order in insight entries in panel 1 on 2021-08-19 (entry 3 precedes entry 2 in time)


``warn_ambiguous_paths``
''''''''''''''''''''''''

When :class:`JSONLoader` (with the help of :func:`find_paths`)
finds more than one possible resolution for an ``input`` path,
it either returns the first match if ``warn_ambiguous_paths`` is False or
completes the iteration first and warns when there is more than one path
found if it is True (default).

To give a simple example, consider a directory like this:

.. code-block:: text

   root
   +-- a
   |   \-- a.txt
   |
   +-- b
   |   \-- a.txt
   |
   \-- backup.json


where in ``backup.json`` we have this:

.. code-block:: json

   {
     "paths": [ "a", "b" ],
     "data": [
       {
         "date": "2022-02-02",
         "entries": [
           {
             "time": "20:00+00:00",
             "input": "a.txt"
           }
         ]
       }
     ]
   }

There are two paths that ``a.txt`` could be resolved into: ``a/a.txt``, by
prepending the first path in ``paths``, or ``b/a.txt``, by prepending the
second path in ``paths``.  By default, where ``warn_ambiguous_paths`` is
True, :class:`LoadError` will issue a warning:

.. testsetup:: warn_ambiguous_paths

   import os, tempfile
   from psp.processors.json_processor import *
   tdir = tempfile.TemporaryDirectory()
   root = tdir.name
   os.mkdir(os.path.join(root, 'a'))
   os.mkdir(os.path.join(root, 'b'))
   with open(os.path.join(root, 'a', 'a.txt'), 'x'):
       pass
   with open(os.path.join(root, 'b', 'a.txt'), 'x'):
       pass
   with open(os.path.join(root, 'backup.json'), 'x') as fp:
       fp.write("""\
       {
         "paths": [ "a", "b" ],
         "data": [
           {
             "date": "2022-02-02",
             "entries": [
               {
                 "time": "20:00+00:00",
                 "input": "a.txt"
               }
             ]
           }
         ]
       }
       """)

.. testcleanup:: warn_ambiguous_paths

   tdir.cleanup()
   del root, tdir

.. doctest:: warn_ambiguous_paths

   >>> from os.path import join
   >>> loader = JSONLoader(error_on_warning=True)
   >>> loader.configure(base_dir=root)
   >>> with open(join(root, 'backup.json'), encoding='utf-8') as fp:
   ...     list(loader.load(fp))
   ...
   Traceback (most recent call last):
     ...
   psp.processors.json_processor.LoadWarning: found more than one path for 'a.txt'; using the first path found '.../a/a.txt' (base_dir = '...')

(The three dots in the exception message are a mere placeholder.  What's
actually printed is whatever the absolute path *root* has.)

.. And of course, for doctest to work with the ELLIPSIS extension...

Note that you won't have this awkward issue if you wrote overlapping
patterns, like ``['a', 'a']`` (see :func:`get_lookup_paths` for how the
lookup paths are actually determined.)  This is because there could be
inevitable overlapping glob patterns in the ``paths`` attribute.


``json_options``
''''''''''''''''

The ``json_options`` option is only used by the
:meth:`JSONLoader.load_json` method, which describes
extra keyword arguments to pass to :func:`json.load`.
It's kind of pointless but maybe some people might find this
useful (perhaps better than subclassing and overriding
:meth:`JSONLoader.load_json`, I don't know???)

>>> import decimal
>>> options = dict(parse_float=decimal.Decimal)
>>> # Subclassing JSONLoader so that we can see the options taking effect
>>> class TestLoader(JSONLoader):
...     def split_data(self, data):
...         data, attrs = super().split_data(data)
...         print('attrs:')
...         for key, value in sorted(attrs.items()):
...             print(f'  {key}: {value!r}')
...         return data, attrs
...
>>> # Mimic a JSON file for load_json() to load from
>>> import io
>>> fp = io.StringIO('{"num": 4.20}')
>>> _ = list(TestLoader(json_options=options).load(fp))
attrs:
  num: Decimal('4.20')
  paths: ['.']
  tz: None


Extensions
^^^^^^^^^^

This section is rather advanced IMO so I put it as the last part of the
Loading section.  Basically, to add support for panel and entry extensions,
:meth:`process_panel` and :meth:`process_entry` are broken down into three
methods:

*  ``get_*_extensions()`` receives all arguments from ``process_*()`` and
   returns a list of extensions (subclasses of
   |Panel| or |Entry|).
*  ``make_*_class()`` then gets the list of extensions and creates a
   new class based on the extensions.
*  Finally, ``make_*()`` is called with the entry class and all the arguments
   from ``process_*()``.

For reference, the source code definitions for the two methods are precisely
the following::

   class JSONLoader(Configurable):
       def process_panel(self, panel, attrs):
           extensions = self.get_panel_extensions(panel, attrs)
           panel_class = self.make_panel_class(extensions)
           return self.make_panel(panel_class, panel, attrs)

       def process_entry(self, entry, panel, attrs):
           extensions = self.get_entry_extensions(entry, panel, attrs)
           entry_class = self.make_entry_class(extensions)
           return self.make_entry(entry_class, entry, panel, attrs)

.. method:: JSONLoader.get_panel_extensions(panel, attrs)

   Get a list of |Panel| subclasses, with the first base class coming
   last in the list.  The parameters are precisely those from
   :meth:`process_panel`.

   Default implementation always returns ``[]``.

.. method:: JSONLoader.make_panel_class(extensions)

   Create a panel class from the list of extensions returned by
   :meth:`get_panel_extensions`.  The list of extensions is reversed and
   |Panel| itself is appended to it.  The only time a new class isn't
   created is when ``extensions`` is an empty list, in which case |Panel|
   is returned.  Otherwise, a newly created class is returned: if we denote
   *extensions* with ``e[0], e[1], ..., e[n-1]`` where
   ``n = len(list(extensions))`` is at least 1, then the class is created
   in a way analogous to ::

      class PanelWithExtensions(e[n-1], e[n-2], ..., e[0], Panel):
          __slots__ = ()

      PanelWithExtensions.__name__ = 'Panel[{}]'.format(
         ', '.join((b[0], b[1], ..., b[n-1]))

   where ``b[i]`` denotes the *extension name* of the panel.

.. method:: JSONLoader.make_panel(panel_class, panel, attrs)

   Create a panel object from *panel*.  This implements most of
   :meth:`process_panel`.  *panel_class* is from :meth:`make_panel_class`
   and the rest of the arguments are from :meth:`process_panel`.

.. method:: JSONLoader.get_entry_extensions(entry, panel, attrs)

   Get a list of |Entry| subclasses, with the first base class coming
   last in the list.  The parameters are precisely those from
   :meth:`process_entry`.

   Default implementation always returns ``[]``.

.. method:: JSONLoader.make_entry_class(extensions)

   Create an entry class from the list of extensions returned by
   :meth:`get_entry_extensions`.  The list of extensions is reversed and
   |Entry| itself is appended to it.  The only time a new class isn't
   created is when ``extensions`` is an empty list, in which case |Entry|
   is returned.  Otherwise a new class is created with a similar algorithm
   to :meth:`make_panel_class`.

.. method:: JSONLoader.make_entry(entry_class, entry, panel, attrs)

   Create an entry object from *entry*.  This implements most of
   :meth:`process_entry`.  *entry_class* is from :meth:`make_entry_class`
   and the rest of the arguments are from :meth:`process_entry`.


-------
Dumping
-------

There isn't one definitive way to generate a unique backup file from a
stream of panels; the easiest way would be to not rely on any sort of
inference and provide every piece of information explicitly, however that
would make the exported output an eyesore.  The goal of :class:`JSONDumper`,
therefore, is to provide a sensible *default* way to export panels that
*tries* to produce a minimal output by excluding information that could be
inferred by :class:`JSONLoader`, given a proper (ideally identical) file
context and inference manager, while at the same time create an interface
as flexible and customizable as possible to get everyone's desired output.

It's hard to say there is a best way to reverse the process of loading,
but it's fair to say it comes down to two things: the JSON file we are
dumping to, and a base directory where ``input`` paths are read from.
That is, with a loading process that looks like this::

   loader = JSONLoader()
   loader.configure(base_dir='path/to')
   with open('path/to/backup.json', encoding='utf-8'):
       panels = loader.load(fp)

The dumping process should look like this; nothing more, nothing less::

   dumper = JSONDumper()
   dumper.configure(base_dir='some/other/path/to')
   with open('some/other/path/to/backup.json', 'x', encoding='utf-8'):
       dumper.dump(panels, fp)

The only difference is that we're *writing* now instead of *reading*!
So, do expect ``base_dir`` to be polluted with files, because while we
won't override any existing files, we might create a mess given how
directories will be implicitly created!  (The ``assets`` directory
relative to ``base_dir`` is the only one created by default, by the way.)

Theoretically, if ``panel`` is a list of |Panel| objects, then ::

   panels == list(loader.load_data(dumper.dump_data(panels)))

will *always* hold regardless of what ``panels`` is.
For a proper pair of loader and dumper like this, I recommend making
sure that:

*  their ``base_dir`` options point to the same directory path
   (unless all data is encapsulated within the backup and no entries
   are exported),
*  their inference managers are identical, and
*  their file type contexts are the same.

Although if ``data`` is a JSON archive as a *dict*, then ::

   data == dumper.dump_data(loader.load_data(data))

isn't necessarily true, since there are more than one way to represent a
panel (and its entries recursively) in JSON.

.. exception:: DumpError

   Error that occured while loading a JSON file; subclass of
   :class:`ValueError`.

.. exception:: DumpWarning

   Warning that occured while loading a JSON file.

.. class:: JSONDumper(**options)

   The JSON backup file dumper class.  This class inherits from
   :class:`~psp.types.Configurable` just like :class:`JSONLoader`, though
   same as before, we will only use the |Configurable.configure| method in
   the examples that are to follow.

   .. warning::

      Since the default option for ``base_dir`` is ``'.'``, i.e. the
      current working directory, be cautious when you don't explicitly
      provide one!  With default implementation of :meth:`get_input_path`,
      and :meth:`use_inline_text`, entries whose |is_text| method returns
      False are always exported to the ``assets`` directory relative to
      ``base_dir``.  So make sure all entries have their |is_text| method
      return True when you choose to omit the ``base_dir``!

      .. |is_text| replace:: :meth:`~psp.types.Entry.is_text`

   .. method:: configure(**options)

      Configure options.
      This is inherited from :class:`~psp.types.Configurable`.

      The following is a table of all options.

      +----------------------------+---------------------------+----------------------+-----------+
      | Option                     | Description               | Type                 | Default   |
      +============================+===========================+======================+===========+
      | ``base_dir``               | Base directory that       | *str* or             | ``None``  |
      |                            | files will be exported    | :class:`os.PathLike` |           |
      |                            | relative to. (1)          | or None              |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``json_options``           | Keyword arguments to      | *dict*               | ``{}``    |
      |                            | pass to ``json.dump()``.  |                      |           |
      |                            |                           |                      |           |
      |                            |                           |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``data_encoder``           | Function that is used to  | callable             | \(2)      |
      |                            | write inline binary       |                      |           |
      |                            | entries.                  |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``paths``                  | Lookup paths; used as the | *list* of path-like  | ``['.']`` |
      |                            | JSON top-level attribute  | objects (3)          |           |
      |                            | ``paths``.                |                      |           |
      |                            |                           |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``time_zone``              | Time zone; used as the    | ``datetime.tzinfo``  | ``None``  |
      |                            | top-level attribute       | instance or ``None`` |           |
      |                            | ``tz`` and is converted   |                      |           |
      |                            | into the JSON top-level   |                      |           |
      |                            | attribute ``tz`` using    |                      |           |
      |                            | :meth:`format_timezone`.  |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``suppress_warnings``      | If true, all              | *bool*               | ``False`` |
      |                            | :exc:`DumpWarning`        |                      |           |
      |                            | is suppressed.            |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+
      | ``error_on_warning``       | If true, all              | *bool*               | ``False`` |
      |                            | :exc:`DumpWarning`        |                      |           |
      |                            | is raised as              |                      |           |
      |                            | exceptions. (4)           |                      |           |
      +----------------------------+---------------------------+----------------------+-----------+

      Notes:

      (1)
         When ``base_dir`` is None, calling any of these methods results in
         a :class:`DumpError`:

         *  :meth:`generate_export_path`
         *  :meth:`export_entry`
         *  :meth:`compute_input_path`

      (2)
         The function in the ``data_encoder`` option should take the entry
         being written and return a tuple ``(data_encoding, data)``, where
         the two values are strings that will be written to the
         ``data-encoding`` and ``data`` attributes by
         :meth:`write_entry_binary_data`.

         Default value::

            def data_encoder(entry):
                return 'base64', base64.b64encode(entry.get_raw_data()).decode('ascii')

      (3)
         The list of paths is always converted to strings by calling
         ``os.fspath()`` on each item.

      (4)
         This has no effect if ``suppress_warnings`` is true.

      More on the usage of these options in the
      :ref:`Options <json_dumper_options>` section.

      The :meth:`dump` and :meth:`dump_data` are the two high-level methods
      used to dump an archive, completely analogous to
      :meth:`load() <JSONLoader.load>` and
      :meth:`load_data() <JSONLoader.load_data>`.  The :meth:`dump` method
      writes panels to a file, while the :meth:`dump_data` method dumps to
      a *dict*.  Again, :meth:`dump` calls :meth:`dump_data` to create a
      *dict* and :meth:`dump_json` to write to the JSON file.
      The implementation of :meth:`dump` is precisely the following::

         def dump(self, panels, fp, *, attrs=attrs):
             data = self.dump_data(panels)
             self.dump_json(data, fp, attrs=attrs)

      At first glance, it might seem weird how we have such an
      asymmetrical option for :meth:`dump` but not :meth:`load`.
      As we will document shortly, this optional *attrs* parameter is
      particularly useful when attributes aren't generated dynamically
      based on the state of the dumper (like a description string);
      that is the job of :meth:`prepare_backup`.
      (As an aside, :class:`JSONLoader` gets all the top-level
      attributes it needs from the JSON data itself, so it doesn't
      need such an awkward option.)

   .. method:: dump(panels, fp, *, attrs=None)

      Dump an iterable of panels to a file.

      :param panels: Any iterable of |Panel| objects.  This includes a
                     sequence (*list* and *tuple*), a generator, or an
                     iterator.
      :param fp: A file-like object implementing the ``write()`` method
                 that accepts a *str*.
      :param attrs: An optional mapping (such as :class:`dict`) of JSON
                    top-level attributes to put at the beginning of the
                    archive.

      With default implementation, the iterable is only consumed once,
      creating a panel *dict* with each iteration.

   .. method:: dump_json(data, fp)

      Dump a *dict* as a JSON object to a file.

      :param data: The *dict* to dump.
      :param fp: A file object, same as that from :meth:`dump`.

   .. method:: dump_data(panels, *, attrs=None)

      Dump an iterable of panels to a *dict*.

      :param panels: An iterable of panels, same as that from :meth:`dump`.
      :param attrs: An optional mapping of extra fields to append to the
                    backup, same as that from :meth:`dump`.
      :returns: The JSON archive as a *dict*.

   The dumping process continues with the creation of top-level attributes,
   analogous to the separation of top-level attributes and panels in
   :meth:`~JSONLoader.split_data`.  To make it easier for processing in the
   future, :class:`JSONDumper` distinguishes two kinds of top-level
   attributes: the top-level attributes as Python objects, referred to as
   the TL attributes, and the *JSON* top-level attributes, referred to as
   the JTL attributes.  They both represent the top-level attributes ---
   ``tz`` and ``paths`` specifically --- but one is used for further method
   calls inside Python and one is used for actual output.

   The TL attributes are created by :meth:`get_top_level_attributes`,
   and by default, ``tz`` and ``paths`` are always set.  The JTL attributes
   are created from the TL attributes by :meth:`prepare_backup`, and by
   default, ``tz`` and ``paths`` are set only if they differ from their
   default values, None and ``['.']``.  Note that if there is a JTL
   attribute named ``data``, it would be overridden by :meth:`dump_data`
   without a warning, since that is used for the panel *dict*\ s.

   So, what :meth:`dump_data` does is the following:

   1. Call :meth:`get_top_level_attributes` with the *panels* argument to
      get the TL attributes.  (This argument is untouched, but I'll talk
      about why in the method.)

   2. Create the JTL attributes, populating it with the *attrs* argument
      optionally.
      Call :meth:`prepare_backup` with the TL attributes acquired from
      step 1 to update the JTL attributes.

   3. Set a new list in the *dict* from step 2 under the key ``'data'``.

   4. For each panel in *panels*, call :meth:`wrap_panel` with the panel
      and the TL attribute from step 1 and append the returned *dict* to
      the list in step 3.

   5. Return the *dict*, optionally removing the ``'data'`` attribute
      in case it's just an empty list.

   Here is the source code copied verbatim for your reference::

      def dump_data(self, panels, *, attrs=None):
          py_attrs = self.get_top_level_attributes(panels)
          data = dict(attrs) if attrs is not None else {}
          self.prepare_backup(data, py_attrs)
          if attrs is not None:
              data.update(attrs)
          panel_list = data['data'] = []
          for panel in panels:
              panel_dict = self.wrap_panel(panel, py_attrs)
              panel_list.append(panel_dict)
          if not panel_list:
              del data['data']
          return data


   .. method:: get_top_level_attributes(panels)

      Get top-level attributes of Python objects as a *dict*.  These will
      be used to call :meth:`wrap_panel`.  As I said above, ``tz`` and
      ``paths`` are always be guaranteed to be set.

      The default implementation derives its values directly from the
      options::

         def get_top_level_attributes(self, panels):
             return {'tz': self.get_option('time_zone'),
                     'paths': self.get_option('paths')}

      The *panels* argument is the same as that from :meth:`dump_data`,
      although the default implementation doesn't use it at all (as seen
      in the code).  It was added for subclasses, which I will explain in
      the following note:

      .. note::

         It is impossible to make use of the ``panels`` argument since
         user may pass an iterator and using it would consume it before
         :meth:`dump_data` tries to use it.  However it is still passed
         as an argument because you may decide to always convert
         ``panels`` to a list first so that you can iterate over it.
         For example, here's a subclass that adds a top-level attribute,
         ``count``, which tallies up the entry count in every panel::

            class Dumper(JSONDumper):
                def dump_data(self, panels):
                    return super().dump_data(list(panels))

                def get_top_level_attributes(self, panels):
                    attrs = super().get_top_level_attributes()
                    attrs['count'] = sum(panel.count() for panel in panels)
                    return attrs

   .. method:: prepare_backup(data, attrs)

      Take the top-level attributes from :meth:`get_top_level_attributes`
      as the *attrs* argument and update *data* with the corresponding
      JSON top-level attributes with JSON-serializable values.
      As mentioned above, ``tz`` and ``paths`` are only added when they
      differ from their respective default values.

      .. note::

         The ``'data'`` key will be overridden if you include it in the
         return value of this method!

   After top-level attributes are set, we begin the reverse process of
   :meth:`JSONLoader.process_panel` and :meth:`JSONLoader.process_entry`!
   Keep in mind that the top-level attributes *attrs* come from
   :meth:`get_top_level_attributes`.

   .. method:: wrap_panel(panel, attrs)

      Convert a |Panel| object into a *dict*.

      :param panel: The panel to convert
      :type panel: |Panel| object
      :param dict attrs: Top-level attributes
      :return: A JSON-serializable *dict* representation of the panel.

   .. method:: wrap_entry(entry, attrs)

      Convert an |Entry| object into a dict.

      :param entry: The entry to convert.
      :type entry: |Entry| object
      :param dict attrs: Top-level attributes.
      :return: A JSON-serializable *dict* representation of the entry.

      Note that *entry* in the arguments can be unlinked, in which case
      :meth:`wrap_entry` never tries to omit the date:

      >>> from datetime import date, datetime, timezone
      >>> from psp.types import Panel, Entry
      >>> # with a linked entry, the date is omitted when its
      >>> # date is equal to that of its panel's
      >>> panel = Panel(date(2022, 2, 22))
      >>> entry = Entry(datetime(2022, 2, 22, 16, tzinfo=timezone.utc))
      >>> # make this a text entry otherwise it will be exported
      >>> entry.set_data('hi')
      >>> panel.add_entry(entry)
      >>> # we know that no exporting will happen so it's okay to
      >>> # not provide a base_dir
      >>> dumper = JSONDumper()
      >>> attrs = dumper.get_top_level_attributes([])
      >>> dumper.wrap_entry(entry, attrs)
      {'time': '16:00+00:00', 'data': 'hi'}
      >>> entry.time = datetime(2022, 2, 23, 16, tzinfo=timezone.utc)
      >>> dumper.wrap_entry(entry, attrs)
      {'date-time': '2022-02-23 16:00+00:00', 'data': 'hi'}
      >>> # with an unlinked entry, date will always be included
      >>> panel.remove_entry(entry)
      >>> entry.has_panel()
      False
      >>> dumper.wrap_entry(entry, attrs)
      {'date-time': '2022-02-23 16:00+00:00', 'data': 'hi'}

   .. note::

      The *attrs dict* is never copied in the above two methods, so make
      sure to make a copy and pass that copy down when you need to change
      something, similar to what is mentioned in the note after
      :meth:`JSONLoader.process_entry`.

   Next we need to address something... tricky.  You see, there are up to
   three ways to represent an entry.  One way is using *inline text*:

   .. code-block:: json

      {
        "tz": "UTC",
        "data": [
          {
            "date": "2022-02-22",
            "entries": [
              {
                "time": "14:00",
                "data": "it's twosday"
              }
            ]
          }
        ]
      }

   Though this is exclusive to text entries that can be fully represented
   by the return value of their :meth:`~psp.types.Entry.get_data` method,
   which, for instance, wouldn't work for images and big entries.  Another
   way that works for *both* text and binary entries is to link the binary
   stream of data from an external file:

   .. code-block:: json

      {
        "tz": "UTC",
        "data": [
          {
            "date": "2022-02-22",
            "entries": [
              {
                "time": "14:00",
                "input": "file.txt"
              }
            ]
          }
        ]
      }

   (Note that because :mod:`~psp.filetypes` by default associates the
   ``.txt`` extension with ``plain``-type entries, :class:`JSONDumper`
   drops information about the type (and encoding too since it can be
   inferred from the type).)  A third way is to use *inline binary*,
   which encodes the binary stream of data inside the backup file:

   .. code-block:: json

      {
        "tz": "UTC",
        "data": [
          {
            "date": "2022-02-22",
            "entries": [
              {
                "time": "14:00",
                "encoding": "utf-8",
                "data": "aXQncyB0d29zZGF5",
                "data-encoding": "base64"
              }
            ]
          }
        ]
      }

   (Note that only the encoding is provided since the ``plain`` type can
   be inferred from any non-``binary`` encoding.)

   .. The three JSON values are produced with this

      from datetime import timezone
      from psp.processors import JSONLoader, JSONDumper
      from os.path import join
      from textwrap import indent
      from tempfile import TemporaryDirectory

      class ExportAll(JSONDumper):
          __slots__ = ()
          def get_input_path(self, entry, attrs):
              self.export_entry(entry, 'file.txt')
              return 'file.txt'

      class InlineBinary(JSONDumper):
          __slots__ = ()
          def get_input_path(self, entry, attrs):
              return None
          def use_inline_text(self, entry):
              return False

      panels = list(JSONLoader().load_data({
          'tz': 'UTC',
          'data': [
              {'date': '2022-02-22',
               'entries': [
                   {'time': '14:00',
                    'data': "it's twosday"}
               ]}
          ]
      }))

      for dumper, name in [(JSONDumper(), 'inline text'),
                           (ExportAll(), 'external file'),
                           (InlineBinary(), 'inline binary')]:
          with TemporaryDirectory() as root:
              dumper.configure(base_dir=root,
                               time_zone=timezone.utc,
                               json_options={'indent': 2})
              with open(join(root, 'backup.json'), 'x+') as fp:
                  dumper.dump(panels, fp)
                  fp.seek(0)
                  print(f'{name}:')
                  print('   .. code-block:: json')
                  print()
                  print(indent(fp.read(), ' ' * 6))
                  print()

   The last two representations work on any entry, but the first one,
   namely *inline text*, only works on a specific subset of entries.
   When an entry is not being exported, whether inline text is used is
   controlled by :meth:`use_inline_text`: it takes the entry as input and
   returns True for inline text or False for inline binary.

   .. method:: use_inline_text(entry)

      Return whether an entry can and will be fully represented with
      inline text.  This method is only called when an entry is *not*
      being exported.  Default implementation returns ``entry.is_text()``.

   Note that returning False is always applicable, but returning True isn't.

   Whether an entry is exported is controlled by :meth:`get_input_path`,
   which receives the same arguments as :meth:`wrap_entry` and either
   returns a *str* to be used in the ``input`` attribute (after the file
   it refers to exists) or None, which would fall back to inline text or
   inline binary, determined by :meth:`use_inline_text` mentioned before.

   The :meth:`get_input_path` has side effects as a file could be created
   in ``base_dir`` when it is called.  This is because the method actually
   does two things when an entry is "exported": generating a potentially
   valid input path and creating the file it refers to or finding an
   existing file with matching what :meth:`~psp.types.Entry.get_raw_data`
   returns; the default implementation always exports to a new path,
   a three-digit suffix (like ``name_001.txt``) whenever necessary.
   However, if an entry is not exported and None is being returned,
   :meth:`get_input_path` should not create any files.

   In addition, if ``base_dir`` is set to None, any attempt to generate a
   new path immediately fails.  As an example, observe what happens when we
   export a binary entry:

   >>> from psp.types import Entry
   >>> from datetime import datetime, timezone
   >>> entry = Entry(datetime(2022, 2, 22, tzinfo=timezone.utc))
   >>> dumper = JSONDumper()
   >>> # is_text() returns False, so by the implementation of
   >>> # get_path() dumper will see this as a binary entry
   >>> entry.is_text()
   False
   >>> # the default value is None
   >>> dumper.get_option('base_dir') is None
   True
   >>> attrs = dumper.get_top_level_attributes([])
   >>> JSONDumper().wrap_entry(entry, attrs)
   Traceback (most recent call last):
     ...
   psp.processors.json_processor.DumpError: base_dir must be set when calling generate_export_path()

   .. XXX: One drawback of implementing get_input_path() this way (exhibiting
      behavior as shown above) is that we are forcing the user to export with
      the default implementation...
      I guess it depends on what users like in general, given how anyone who
      prefers using binary inline would necessarily have to override the
      class, which is of little cost IMO compared to having users forget to
      provide a base_dir and end up getting a bunch of base64 junk in their
      backup file :/

   .. method:: get_input_path(entry, attrs)

      Get an input path for the entry.  The arguments passed are the
      exact same from :meth:`wrap_entry`.  Return a *str* for using
      ``input`` to include an external path or None for using inline
      text/binary.

   .. note::

      Implementation of :meth:`get_input_path` should not worry about
      returning a valid input path.  When a *str* is returned,
      :meth:`wrap_entry` will check if the file matched by the input path
      has content identical to that of the entry.  (This also means a new
      file does not necessarily have to be created as long as you are able
      to point at a file with matching content!  Default implementation,
      of course, always creates a new file.)

   By default :meth:`get_input_path` always exports to the ``assets``
   directory, which can be seen in the default implementation
   (I'll explain this in a bit)::

      def get_input_path(self, entry, attrs):
          # by default we don't keep entries that don't have
          # a sufficient text representation.
          if self.use_inline_text(entry):
              return None
          back, front = self.get_export_path_directory(entry)
          base, ext = self.get_export_path_name(entry)
          paths = attrs['paths']
          # glue the front component to the base file name
          filename = self.generate_export_path(
              entry, os.path.join(front, base), ext, back, paths)
          # ensure that this new file exists
          self.export_entry(entry, os.path.join(back, filename))
          # arbitrarily extend the input path by the back component
          return self.compute_input_path(filename, back, paths)

   .. sorry for breaking the 80 char limit there :c
      imo i prefer it on one line....

   First off, the use of :meth:`use_inline_text` is to simply make sure
   that text entries are never exported.  Generally :class:`JSONDumper`
   prefers exporting to inline binary, so only entries that can be fully
   represented with inline text (determined by :meth:`use_inline_text`
   returning True) cause :meth:`get_input_path` to return None (that is,
   they are kept inside the backup).  The next two lines call
   :meth:`get_export_path_name` to form an appropriate file name for the entry.

   The next three method calls are what I'm going to explain in depth:
   :meth:`generate_export_path`, :meth:`export_entry`, and
   :meth:`compute_input_path`.  Before I do that, let me list out some
   seriously belated terminology here:

   *  An *input path* is any "sub-path" of a *relative path* --- a file's
      path relative to ``base_dir``.  For example, for a relative path
      ``img/a/1.jpg``, the strings ``1.jpg``, ``a/1.jpg``, and
      ``img/a/1.jpg`` itself are all its valid input paths.

   *  We say an input path is *reachable* when an existing file path equals
      some *lookup path* joined with the input path.  A lookup path in this
      sense is a concrete directory path matching a pattern in the ``paths``
      attribute (see :func:`get_lookup_paths`).  For example, the
      ``img/a/1.jpg`` relative path is reachable when the ``img/`` lookup
      path is joined with the input path ``a/1.jpg``.

   *  We say a reachable input path is *unambiguous* when it is reachable
      when joined with precisely one lookup path; a reachable input path
      is ambiguous otherwise (reachable with more than one lookup path).
      For example, with lookup paths ``./``, ``img/``, and ``assets/``,
      the input path ``a/1.jpg`` is only unambiguous when precisely one of
      the three relative paths exists:

      .. code-block:: text

         ./[a/1.jpg]
         img/[a/1.jpg]
         assets/[a/1.jpg]

      The square brackets will be used to denote the input path in a
      relative path.  The above relative paths are collectively called the
      *candidate paths*, which need not exist, but it's a convenient term
      for us to use to refer to these later on.

   *  To keep things short, I will be using ``join(a, b, c, ...)`` to denote
      path concatenation using :func:`os.path.join`.

   So what do the three methods do here?  Well, briefly:

   *  :meth:`generate_export_path` essentially returns ``base + ext`` but
      modifies ``base`` appropriately to avoid the creation of ambiguous
      input paths.

   *  :meth:`export_entry` writes the content of an entry to a relative
      path, creating intermediary directories without warnings.

   *  :meth:`compute_input_path` returns the *shortest unambiguous* input
      path that can reach ``join(dirname, name)``.  If that is impossible,
      return ``join(dirname, name)``.

   .. XXX: This is a mess we probs should put this in a separate section

   To motivate you with why it was made this way, consider the case where
   we would like to export to ``assets/1.txt``.  What :meth:`get_input_path`
   does breaks down to the following calls::

      def get_input_path(self, entry, attrs):
          paths = attrs['paths']
          name = self.generate_export_path(entry, '1', '.txt', 'assets', paths)
          self.export_entry(entry, join('assets', name))
          return self.compute_input_path(name, 'assets', paths)

   The last step with :meth:`compute_input_path` is probably the most
   intuitive to understand, because with different *paths* you would need
   to select the appropriate input paths, which could be ``1.txt`` or
   ``assets/1.txt``.  For example the former would be selected if the
   ``assets`` directory is in *paths*, and the latter would be selected if
   the base directory ``.`` is in *paths*; whichever is shorter is preferred.
   (The rules aren't exactly like that though.  For example if
   ``paths = ['assets', 'doc', '.']`` and ``doc/1.txt`` exists, then
   :meth:`compute_input_path` would not use ``1.txt`` as an input path
   since it causes ambiguity known at runtime.)

   But just having the input path unambiguous at runtime isn't enough.
   Again, recall that *any* sub-path of an export path can be a potential
   input path, and by claiming ``assets/1.txt`` to be your new file name,
   you're risking the possibility of taking up one of the candidate paths of
   any of these sub-paths.  To give a super contrived example, let's say
   ``paths = ['.', 'assets']`` and we're still exporting to ``assets/1.txt``,
   except there already is a file oddly named ``assets/assets/1.txt``, whose
   input path ``assets/1.txt`` was determined unambiguous in a prior call to
   :meth:`get_input_path`.  By going through the same logic,
   :meth:`compute_input_path` arrives at the conclusion that ``1.txt`` is the
   shortest unambiguous input path and sees that with the lookup path
   ``assets`` derived from *paths* and returns it.  However ``assets/1.txt``
   is in fact one of the candidate paths for the input path ``assets/1.txt``,
   and by exporting to that path we run into a problem: ``assets/1.txt`` is
   no longer unambiguous.

   .. code-block:: text

         Candidate paths for ``assets/1.txt`` | Candidate paths for ``1.txt``
         -------------------------------------+------------------------------
         ./[assets/1.txt]                     | ./[1.txt]
         ./assets/[assets/1.txt]              | ./assets/[1.txt]

   In this case, the ambiguous input path ``assets/1.txt`` is long enough to
   go unnoticed for :meth:`compute_input_path`, but regardless
   this poses a serious problem: it is not possible (not practical to say
   the least) to "rename" that previously exported ``assets/1.txt``, and by
   simply selecting the right sub-path for input path isn't going to fix that
   ambiguity since the file path we are exporting to is regardless going to
   be in the candidate paths of some other input path (in this case,
   ``assets/assets/1.txt``).

   This is exactly where :meth:`generate_export_path` comes in;
   it renames the path that we are about to export to avoid the above scenario
   from happening in the first place.  In this case in particular,
   :meth:`generate_export_path` iterates over all possible input paths
   (``1.txt`` and ``assets/1.txt``) and sees if any of them matches an
   existing file (ignoring the extension, so finding ``1.jpg`` or ``1.md``
   would look the same to :meth:`generate_export_path`).  If it does, then
   it appends a numerical suffix to the file name such as ``1_001.txt`` and
   ``1_002.txt`` (assuming a default implementation of
   :meth:`get_export_path_candidates`) and repeats the same process.
   Once the file name is good to go, it returns the file name.

   And now let me briefly talk about why the directory name and base name
   are separated.  As an example, let's say you have two audio files
   ``rec/cat.mp3`` and ``mus/cat.mp3``, but you don't want
   :class:`JSONDumper` to rename either one of them.  One way is to make
   the directory a part of its "file name" so that :class:`JSONDumper`
   does not try to tear them apart:

   .. code-block:: python

      self.generate_export_path(entry, 'rec/cat', '.mp3', '.', paths)
      self.generate_export_path(entry, 'mus/cat', '.mp3', '.', paths)

   This, however, comes at a risk.  By skipping the shorter components
   like ``cat.mp3`` in the process of checking for ambiguity, we are subject
   to ill-defined lookup paths that may cause :meth:`generate_export_path` to
   overlook ambiguity brought about by ``cat.mp3``.  As I will elaborate on
   later, :meth:`generate_export_path` would issue a :class:`DumpWarning`
   when such ambiguity becomes problematic.

   .. method:: generate_export_path(entry, base, ext, dirname, paths)

      Generate a file name for exporting by combining *base* and *ext*
      in a way the file name doesn't collide with any existing file.

      .. important::

         The only scenario :meth:`generate_export_path` returns a file
         name that points to an *existing* file is when that file has
         matching content compared to *entry*.
         If you want to have this return a new file every time,
         override :meth:`export_path_ok`::

            def MyDumper(JSONDumper):
                def export_path_ok(self, entry_path, entry):
                    return os.path.exists(entry_path)

      :param entry: The entry that this export path will be generated for
      :type entry: |Entry| object
      :param str base: The component of the export path that this method
                       should start checking from, stripped of its file
                       extension
      :param str ext: The file extension
      :param dirname: The other component of the export path aside from
                      *base* as a path-like object
      :param list paths: The *paths* top-level attributes

      :return: ``base_0 + ext``, where ``base_0`` is the first string
               generated from :meth:`get_export_path_candidates` that
               causes no ambiguity

      More specifically, this method iterates over a generator of candidates
      to use in place of *base*
      (returned by :meth:`get_export_path_candidates`).
      For each ``base_0`` in that generator, ``base_0 + ext`` is used to
      form the *name* of the file, and *name* is returned if:

      *   ``join(dirname, name)`` does not exist *or* the file exists
          and has matching content compared to the entry
          (to change this behavior, see :meth:`export_path_ok`)
      *   *name* is unreachable with the *paths* argument, and
      *   any extended version of *name* with a number of path components from
          *dirname* is unreachable with the *paths* argument.

      As an example, here are the file paths checked for when called with
      arguments ``('d/e/1', '.txt', 'a/b/c', paths)`` (ignoring the entry):

      *  ``d/e/1.txt`` (or any file whose base file name is ``1`` in ``d/e``)
      *  ``c/d/e/1.txt`` (similarly from here on)
      *  ``b/c/d/e/1.txt``
      *  ``a/b/c/d/e/1.txt``

      .. warning::

         Currently ``dirname`` in :meth:`generate_export_path` and
         :meth:`compute_input_path` is always normalized, so if you pass
         ``'assets/./../img'`` it is simply treated as ``'img'``.

         I haven't tested with ``base`` in :meth:`generate_export_path`
         though (since like I said with the ``base + ext`` analogy, it only
         does a simple string concatenation and doesn't normalize the path),
         but I can't guarantee non-normalized paths work there.

      :raise ValueError:
         When *ext* contains a path separator

      :raise DumpError:
         If the ``base_dir`` option is ``None`` or when
         :meth:`get_export_path_candidates` is exhausted

      :raise DumpWarning:
         If any sub-path of *name*, as in input path, *could* be reachable
         with an ill-defined *paths*.
         (This will never be issued if *name* has no directory component)

      To give an example that would raise a :class:`DumpWarning`, imagine if
      we want to export to the following files:

      .. code-block:: text

         .
         +-- 1.txt           <-- (1) first export this
         |
         \-- a/
             \-- 1.txt       <-- (2) then this

      And the lookup paths expand to ``['a', '.']``.
      To export the first entry, we call ::

         self.generate_export_path(entry, '1', '.txt', '.', paths)

      and ``1.txt`` is returned because ``1.txt`` is reachable when joined
      with the lookup path ``'.'``.  To export the second entry, we call ::

         self.generate_export_path(entry, 'a/1', '.txt', '.', paths)

      and ``a/1.txt`` is returned because ``a/1.txt`` is reachable when
      joined with the lookup path ``'a'``.  But notice how because we
      skipped the process of checking the smaller components of ``a/1.txt``,
      we did not check those components as possible input paths that *could*
      match the file we are exporting to.  In our case, the file path
      ``a/1.txt`` is reachable by the smaller input path ``1.txt``, and our
      first entry is now pointing towards the file ``a/1.txt`` instead of
      the file ``1.txt``.

      Another way to assert this fact is that some directory of *name* can be
      matched by the lookup paths.  In this case, ``a`` is a directory of
      ``1.txt`` and ``a`` is clearly matched by the lookup paths.  A benefit
      of asserting it this way is that we do not need to wait for the moment
      when the program is about to break, i.e. when an entry is already
      exported with the shorter input path ``1.txt``.

      .. TODO: include this in doctest

      To see what we said in action, consider the following code that
      implements the preceding example::

         from psp.processors import JSONLoader, JSONDumper
         import io, json, tempfile

         class DemoDumper(JSONDumper):
             def get_input_path(self, entry, attrs):
                 paths = attrs['paths']
                 if entry.get_data() == 'ONE':
                     filename = self.generate_export_path(entry, '1', '.txt',
                                                          '.', paths)
                 elif entry.get_data() == 'TWO':
                     filename = self.generate_export_path(entry, 'a/1', '.txt',
                                                          '.', paths)
                 # join('.', filename) would be identical to just... filename,
                 # so I'm skipping that here.
                 self.export_entry(entry, filename)
                 return self.compute_input_path(filename, '.', paths)

         with tempfile.TemporaryDirectory() as root:
             panels = JSONLoader().load(io.StringIO("""\
                 {
                   "tz": "UTC",
                   "data": [ { "date": "2022-02-22",
                               "entries": [
                                 { "time": "01:00", "data": "ONE" },
                                 { "time": "02:00", "data": "TWO" }
                               ]
                           } ]
                 }
             """))
             DemoDumper(base_dir=root, paths=['a', '.']).dump_data(panels)

      If we run this, we get (with a bit of line wrapping)

      .. code-block:: text

         .../psp/processors/json_processor.py:1291:
         DumpWarning: 'a/1.txt' is not the shortest reachable path for 'a/1.txt'
         (parent directory 'a' matches the lookup path 'a'); name collisions may occur
           self._warn(

      More generally, if we had a longer *name*, say ``a/b/c/d/e/1.txt``,
      accompanied by some *dirname* ``root`` then the *directories* checked
      for are:

      *  ``join(root, 'a')``
      *  ``join(root, 'a/b')``
      *  ``join(root, 'a/b/c')``
      *  ``join(root, 'a/b/c/d')``
      *  ``join(root, 'a/b/c/d/e')``

      If any one of these directories can be matched by *paths*,
      a :class:`DumpWarning` ensues.

      Okay, now we understand how this might be an issue.  How do we
      solve it then?  Well, here are some solutions to think of:

      1. Redefine your *paths* so that no shorter input path can be reachable.
         In this case, consider removing ``'a'`` from your *paths*.

      2. Tell :meth:`generate_export_path` to start from the shortest
         reachable path instead, that is::

            filename = self.generate_export_path(entry, '1', '.txt', 'a', paths)

         Once you've prevented name collisions, then you can call ::

            return self.compute_input_path(join('a', filename), '.', paths)

         later to ensure that ``a`` and ``1.txt`` are always glued together
         in the input path.

   .. method:: export_entry(entry, export_path)

      Export *entry* to an *export_path* relative to the current dumper's
      ``base_dir``, creating intermediary directories as needed.
      **NOTE**: this does nothing if *export_path* exists.

      :param entry: Entry whose data is to be exported
      :type entry: |Entry| object
      :param export_path: Relative path-like object, pointing to a file
                          within ``base_dir`` that doesn't exist at runtime

      :raise DumpError:
         If the ``base_dir`` option is ``None`` or the file path
         ``join(base_dir, export_path)`` points to a path beyond
         ``base_dir`` (e.g. ``export_path = '../1.txt'``, or
         ``export_path`` is absolute)

   .. method:: compute_input_path(name, dirname, paths)

      Compute a valid input path for an existing file at
      ``join(dirname, name)``; return ``join(dirname, name)`` as
      a last resort.

      :param str name: The inseparable component that must be included in
                       the input path
      :param dirname: The other component of the export path aside from
                      *base* as a path-like object
      :param list paths: The *paths* top-level attributes

      :return: The shortest input path that can *unambiguously reach*
               ``join(dirname, name)`` with the provided *paths*

      :raise DumpError:
         If the ``base_dir`` option is ``None``

      Again, a concrete example might help you understand the algorithm
      better.  Let's say we are passed ``('d/e/1.txt', 'a/b/c', paths)``.
      Then input paths are tested in the following order:

      *  ``d/e/1.txt``
      *  ``c/d/e/1.txt``
      *  ``b/c/d/e/1.txt``

      The first unambiguous path in the list is returned.
      Note that ``a/b/c/d/e/1.txt`` is never tested and will always be
      returned if the method doesn't return at any of the preceding
      input paths.

   Auxiliary functions:

   .. method:: get_export_path_directory(entry)

      Return a pair of directory components ``(back, front)`` that,
      when combined, points to the directory to export *entry*
      relative to ``base_dir``.
      ``front`` represents the directory component that must always
      be included in the input path, and ``back`` represents the
      component that may be included.
      Default implementation always returns the string
      ``('assets', '')``.

   .. method:: export_path_ok(export_path, entry)

      Return whether *export_path* is a good export path for
      :meth:`generate_export_path` to use.  Default implementation
      returns True if *export_path* doesn't exist or the content
      matches that of *entry* returned by |stream_raw_data|.

   .. method:: get_export_path_name(entry)

      Return a tuple of ``(base, ext)`` as the file base name
      and file extension for *entry*.

   .. method:: get_export_path_candidates(name)

      Given a base file name, yield a list of candidate names that can
      be used to substitute the name.  Default implementation yields
      ``name``, ``name_001``, ``name_002``, and so forth.

   .. method:: format_timezone(tz)

      Format a :class:`~datetime.tzinfo` object as a *str*.
      The same object should be able to be reconstructed from
      the *str* by :meth:`~JSONLoader.parse_timezone`.

      Default implementation serializes the only known fixed-offset
      timezones, :class:`datetime.timezone`.  The
      :meth:`~datetime.datetime.utcoffset` method will be called
      on :attr:`datetime.datetime.min` with the given time zone,
      and the offset is formatted by :func:`psp.timeutil.format_offset`.

   .. method:: format_date(date)

   .. method:: write_entry_time(entry_dict, dt)

   .. method:: write_entry_date_and_time(entry_dict, dt)

   .. method:: write_entry_type_and_format(entry_dict, e_type, e_format)

   .. method:: write_entry_text_data(entry_dict, entry)

   .. method:: write_entry_binary_data(entry_dict, entry)



.. _json_dumper_options:

Dumper Options
^^^^^^^^^^^^^^

``base_dir`` (dumper)
'''''''''''''''''''''


---------------------
Lookup Implementation
---------------------

.. function:: find_paths(path, base_dir, paths)

   Generator for stuff

.. function:: get_lookup_paths(base_dir, paths)

   What :func:`find_paths` also uses

   for example, if ``'a*'`` and ``'*b'`` in a file system where
   ``ab/`` and ``ac/`` and ``bc/`` exist, then only ``ab`` and ``ac``
   are lookup paths


------------------
Inference Managers
------------------

.. class:: InferenceManager

   stuff


---------------------
Convenience Interface
---------------------

.. TODO: EXAMPLES!!!!!!

We arrive at last... the nasty does-it-all functions.  Just the obnoxious
number of optional arguments should tell you that something nasty is going
on.  But I thought, maybe, just *maybe*, people will be less intimidated
if they see just one line of code magically doing everything they need!
So here we go...

.. I know this breaks the 80 char limit, but even so don't wrap this
   (it will break)

.. function:: load_json(file, date=None, *, encoding=None, errors=None, cls=JSONLoader, **options)

   Convenience interface to loading JSON archives.

   :param file:
      A file object that implements ``read()`` or a file path where
      :func:`io.open` will be used with the *encoding* and *errors*
      parameters to open the file.  If a file object is passed,
      it remains open after the function call.
   :param date:
      The date of the panel to load.  Can either be a
      :class:`datetime.date` object or a *str*, which will then
      converted with the :meth:`JSONLoader.parse_date` method.
      If omitted, all panels are returned as a list.
   :param str encoding:
      Parameter for :func:`io.open`
   :param str errors:
      Parameter for :func:`io.open`
   :param loader:
      The :class:`JSONLoader` object to use.  Should implement
      :meth:`~JSONLoader.load` and :meth:`~JSONLoader.parse_date`
      methods like :class:`JSONLoader` does.  If one isn't provided,
      a new :class:`JSONLoader` instance is created with additional
      keyword arguments passed to this function.
   :returns:
      A *list* of panels, or the first panel whose
      :attr:`~psp.types.Panel.date` equals the *date* argument.

.. function:: dump_json(panels, file, *, attrs=None, exist_ok=False, encoding=None, errors=None, cls=JSONDumper, **options)

   Convenience interface to dumping JSON archives.

   :param panels:
      An iterable of panels.  Parameter for :meth:`~JSONDumper.dump`.
   :param file:
      A file object that implements ``write()`` or a file path where
      :func:`io.open` will be used with the *encoding* and *errors*
      parameters to open the file.  If a file object is passed,
      it remains open after the function call.
   :param attrs:
      Parameter for :meth:`~JSONDumper.dump`.
   :param bool exist_ok:
      If true, use the ``w`` mode to open the file.
      Otherwise the ``x`` mode is used.
   :param str encoding:
      Parameter for :func:`io.open`
   :param str errors:
      Parameter for :func:`io.open`
   :param dumper:
      Dumper object to use.  Should implement a
      :meth:`~JSONDumper.dump()` method like :class:`JSONDumper` does.
      If one isn't provided, a new :class:`JSONDumper` instance is
      created with additional keyword arguments passed to this function.

Note that the *file* argument in the above functions can either be a file
object and a file path.  Pretty messed up if you ask me, but still...
they're just there in case you need it.


.. |Panel| replace:: :class:`~psp.types.Panel`
.. |Entry| replace:: :class:`~psp.types.Entry`
.. |stream_raw_data| replace:: :meth:`~psp.types.Entry.stream_raw_data`
.. |Configurable.configure| replace:: :meth:`Configurable.configure() <psp.types.Configurable.configure>`
