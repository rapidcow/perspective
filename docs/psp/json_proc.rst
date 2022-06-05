.. _processors_json:

================================================================
:mod:`processors.json_processor` --- JSON backup file processors
================================================================

.. module:: psp.processors.json_processor
   :synopsis: JSON backup file processors

Most of these classes and functions are imported into ``processors``, so
practically you can just write::

    from psp.processors import load_json, dump_json
    # or...
    from psp.processors import JSONLoader, JSONDumper

instead of the whole long name...


.. contents::
   :local:
   :depth: 1

-------
Loading
-------

.. exception:: LoadError

   Exception raised by :class:`JSONLoader`.

.. exception:: LoadWarning

   Warning warned or raised by :class:`JSONLoader`.

.. class:: JSONLoader(**options)

   The JSON backup file loader class.

   The constructor takes no positional arguments, and all keyword
   arguments are passed to the :meth:`configure()` method.

   .. method:: configure(**options)

      Configure options.  The following are a table of all options.

      +----------------------------+--------------------------+-----------------+-----------------+
      | Option                     | Description              | Type            | Default         |
      +============================+==========================+=================+=================+
      | ``check_panel_order``      | If true, warn on         | *bool*          | ``True``        |
      |                            | panel dates that are     |                 |                 |
      |                            | not strictly             |                 |                 |
      |                            | increasing. (1)          |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``check_entry_order``      | If true, warn on         | *bool*          | ``True``        |
      |                            | entry times that are     |                 |                 |
      |                            | not consistently         |                 |                 |
      |                            | increasing. (2)          |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``check_panel_duplicates`` | If true, warn on         | *bool*          | ``False``       |
      |                            | panels that have         |                 |                 |
      |                            | repeated dates. (3)      |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``suppress_warnings``      | If true, all             | *bool*          | ``False``       |
      |                            | :exc:`LoadWarning`       |                 |                 |
      |                            | is suppressed.           |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``error_on_warning``       | If true, all             | *bool*          | ``False``       |
      |                            | :exc:`LoadWarning`       |                 |                 |
      |                            | is raised as             |                 |                 |
      |                            | exceptions. (4)          |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``paths``                  | Extra lookup paths for   | iterable        | ``()``          |
      |                            | parsing the *input*      |                 |                 |
      |                            | field for entries.       |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``warn_ambiguous_paths``   | If true, warn for        | *bool*          | ``True``        |
      |                            | paths are found more     |                 |                 |
      |                            | than once.               |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``base_dir``               | Base directory for       | *str* or        | ``os.getcwd()`` |
      |                            | relative *input* paths   | ``os.PathLike`` |                 |
      +----------------------------+--------------------------+-----------------+-----------------+
      | ``json_options``           | Keyword arguments to     | *dict*          | ``{}``          |
      |                            | pass to ``json.loads()`` |                 |                 |
      +----------------------------+--------------------------+-----------------+-----------------+

      Notes:

      (1)
         A warning is issued if ``d1 >= d2`` for any two consecutive panels of
         dates ``d1`` and ``d2``.

      (2)
         A warning is issued if ``t1 > t2`` for any two consecutive panels of
         aware date time ``t1`` and ``t2``.  Note that two entries may have the
         same aware date time, but the latter must not be earlier than the
         former.

      (3)
         This has no effect if ``check_panel_order`` is true.

      (4)
         This has no effect if ``suppress_warnings`` is true.


   .. method:: load(file, date=None, *, encoding='utf-8')

      Load an archive from *file*.

   .. method:: load_json(file, date=None)

   These methods are responsible for parsing time-related and can be
   overridden.  Default implementation calls their corresponding
   functions in :mod:`psp.timeutil`.

   .. method:: parse_timezone(s)

      Parses the ``tz`` field, both at top-level and inside an entry.
      This calls :func:`psp.timeutil.parse_timezone`.

   .. method:: parse_datetime(s, *, tzinfo, fold)

      Parses the ``date-time`` field in entry and time fields in meta
      attributes.  The keyword arguments are ``None`` unless they are
      known.  This calls :func:`psp.timeutil.parse_datetime`.

   .. method:: parse_date(s)

      Parses the ``date`` field, both in panel and in entry.
      This calls :func:`psp.timeutil.parse_date`.


Protected Methods
^^^^^^^^^^^^^^^^^

.. method:: JSONLoader._find_path(self, path, dirpaths)

   This is the lookup algorithm used on the *input* field of entries.



-------
Dumping
-------

.. exception:: DumpError

   Error raised by :class:`JSONDumper`.

.. class:: JSONDumper(**options)

   The JSON backup file dumper class.

   .. method:: configure(**options)

      Configure options.

   .. method:: dump(panels, dirname)

      Dump panels to a directory.  *dirname* should be a path-like object to
      the path of the directory.  If the directory already exists, a
      ``FileExistsError`` will be raised by |mkdir|_.

      .. |mkdir| replace:: ``os.mkdir()``
      .. _mkdir: https://docs.python.org/3/library/os.html#os.mkdir


---------------------
Convenience Interface
---------------------

.. function:: load_json(file, date=None, *, encoding='utf-8', **options)

   Convenience interface to loading JSON archives.

.. function:: dump_json(panel, dirname, *, encoding='utf-8', **options)

   Convenience interface to dumping JSON archives.
