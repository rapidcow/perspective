.. _bigentry:

=================================================
:mod:`extensions.bigentry` --- Blog-style entries
=================================================

.. module:: psp.extensions.bigentry
   :synopsis: Very big entries

This module provides support for writing entries that include multiple files!


.. class:: BigEntry(Entry)

   :class:`Entry <psp.types.Entry>` subclass that uses an archive format.

.. class:: BigLoader(JSONLoader)

   :class:`JSONLoader <psp.processors.json_processor.JSONLoader>` subclass
   that reads big entries.

.. class:: BigDumper(JSONDumper)

   :class:`JSONDumper <psp.processors.json_processor.JSONDumper>` subclass
   that writes big entries.
