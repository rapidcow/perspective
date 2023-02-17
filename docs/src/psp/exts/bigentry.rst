.. _ext_bigentry:

=================================================
:mod:`extensions.bigentry` --- Blog-style entries
=================================================

.. module:: psp.extensions.bigentry
   :synopsis: Very big entries

This module provides support for writing entries that include multiple files!

Big entries are a subset of binary entries---entries whose encoding is
``binary`` and is capable of representing a *strictly self-contained*
directory.  The type of a big entry must be one of the registered *archive formats*.
(Note that despite the name "archive *format*", it is not an entry format,
so you must use get_type() and set_type() and not their counterparts
for format.)

.. XXX: do we document the default big entry managers

While a normal entry has a str or a list for its *data* field, a big entry
has a dict instead. That dict must provide the data of the archive and the
archive path to the *main file*. The main file is a text file located in the
archive that represents the main content of the entry.


.. class:: BigEntryManager(abc.ABC)

   Abstract base class for big entry archive type manager.

.. class:: BigEntry

   :class:`~psp.types.Entry` subclass that uses an archive format.

.. class:: BigLoader

   :class:`~psp.processors.json_processor.JSONLoader` subclass
   that reads big entries.

.. class:: BigDumper

   :class:`~psp.processors.json_processor.JSONDumper` subclass
   that writes big entries.
