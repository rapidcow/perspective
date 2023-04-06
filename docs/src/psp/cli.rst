.. _main_program:

=========================================
:mod:`psp.cli` --- Command-line interface
=========================================

.. module:: psp.cli
   :synopsis: Command-line interface

Spec for projects
-----------------

*  ``.psp/config.toml``

   -  ``project.version``: only 0
   -  ``project.config-file``: path to ``config.py``
   -  ``project.entry-point``: path to ``main.py``

*  ``${config-file}``

   -  options prefixed with the name of the subcommand
   -  edit: ``EDITOR`` (e.g. vim)
   -  backup: ``IGNORE`` (e.g. ``['scripts/', 'lib/'])``),
      ``DIR`` (e.g. ``.psp/snapshots``)

all of these are mandatory; in addition, ``config.py`` still
has those functions are less dependent on the library

Plan for subcommands
--------------------

*  **init**: create project, will ask for:

   -  project structure (whether to put scripts within scripts?)
   -  whether to use partitions?
   -  built-in extensions to use?

*  **config**: configuration variables

   -  ``root``: parent directory of ``.psp/``
   -  anything else: reads from ``.psp/config.toml``
   -  additional argument edits the configuration

*  **print**: query panels

   -  date syntax: ``X`` for precise timestamp, ``to Y`` for up to Y,
      ``X to`` for after ``X``, ``X to Y`` for range (all inclusive),
      ``about`` for fuzzy time (within ``TIME_MARGIN_OF_ERROR`` or
      ``DATE_MARGIN_OF_ERROR``), ``give or take`` or ``pm``
      (abbreviation for "plus or minus") for custom margin of error
      (on both bounds, though this is probably more useful on one bound)
   -  don't omit month/minutes please; single digits make no sense
   -  maximize fuzziness when the exact time isn't provided
   -  input time is always parse as naive, ``now`` for current (local)
      time, ``today`` or ``yesterday`` for days (can be used in
      conjunction with time), other than that i don't intend to use
      any other special date name (sorry)
   -  ``--at``, ``-t``: query on entry time
   -  ``--on``, ``-d``: query on panel date
   -  ``--expr``, ``-e``: regex match on text
   -  ``--tz``: time zone to coerce all time into; by default
      local time is used

*  **synopsis**: brief summary (good as it is currently)

*  **shell**: interactive session (don't load panels by default)

   -  ``--load``: load all panels

*  **update**

*  **edit**

*  **backup**


Functions here
--------------
