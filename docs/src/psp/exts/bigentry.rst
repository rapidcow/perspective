.. _ext_bigentry:

=================================================
:mod:`extensions.bigentry` --- Blog-style entries
=================================================

.. module:: psp.extensions.bigentry
   :synopsis: Very big entries

This module provides support for writing entries that include
multiple files!

Big entries are a subset of binary entries---entries whose encoding is
``binary`` and is capable of representing a *strictly self-contained*
directory.  The type of a big entry must be one of the registered
*archive formats*.
(Note that despite the name "archive *format*", it is not an entry
format, so you must use |get_type| and |set_type| and not their
counterparts for format.)

.. XXX: do we document the default big entry managers

While a normal entry has a *str* or a *list* for its ``data`` field,
a big entry has a *dict* instead.  That *dict* must provide the data of
the archive and the archive path to the *main file*.  The main file is
a text file located in the archive that represents the main content of
the entry.  The general structure looks like this:

.. code-block:: json

   {
       "date-time": "2021-12-17 12:00",
       "format": "the archive format",
       "data": {
           "input": "the path to the archive",
           "main-file": "main file within archive",
           "type": "type of the main file",
           "encoding": "encoding of the main file",
           "format": "format of the main file"
       }
   }

Here are some more detailed requirements.  When ``data`` is a *dict*,
it must have:

*  *precisely* one of ``raw`` (paired with ``data-encoding``) and
   ``input``; and
*  the path of the main file within the archive, through ``main-file``.

The ``input`` attribute, if provided, should be a path to the archive.
The ``raw`` attribute, if provided, should be an ASCII-encoded string
capable of being decoded by |JSONLoader|.

The inference rules will work as expected!  So say if ``main-file`` is
``main.txt``, then you can expect the main file type to be ``plain``.

.. class:: BigEntryManager(abc.ABC)

   Abstract base class for big entry archive type manager.

.. class:: BigEntry

   :class:`~psp.types.Entry` subclass that uses an archive format.

   Default values:

   *  *main_file*: unset --- you'll get a :class:`KeyError` if you try
      to call :meth:`get_main_file`
   *  *main_file_type*: ``'plain'``
   *  *main_file_encoding*: ``'utf-8'``
   *  *main_file_format*: ``None``

   I'll just list some boring getters and setters for now
   (they all use the attribute protocol)

   .. method:: get_main_file()
   .. method:: set_main_file(value)
   .. method:: get_main_file_type()
   .. method:: set_main_file_type(value)
   .. method:: get_main_file_encoding()
   .. method:: set_main_file_encoding(value)
   .. method:: get_main_file_format()
   .. method:: set_main_file_format(value)


.. class:: BigLoader

   :class:`~psp.processors.json_processor.JSONLoader` subclass
   that reads big entries.

   .. method:: make_entry(entry_class, entry, panel, attrs)

      Does something magical at the moment (I won't describe how
      it's too hacky)

   .. method:: get_export_path_directory(entry)

      Overridden so that the method returns ``('doc', '')``
      when *entry* is a :class:`BigEntry`.


.. class:: BigDumper

   :class:`~psp.processors.json_processor.JSONDumper` subclass
   that writes big entries.

   .. method:: wrap_entry(entry, attrs)

      Magical just like :meth:`BigLoader.process_entry`

.. |JSONLoader| replace:: :class:`~psp.processors.json_processor.JSONLoader`
.. |get_type| replace:: :meth:`~psp.types.Entry.get_type`
.. |set_type| replace:: :meth:`~psp.types.Entry.set_type`
