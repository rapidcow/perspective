.. _types:

==================================
:mod:`types` --- Important objects
==================================

.. module:: psp.types
   :synopsis: Define panel and entry objects.

This module defines the :class:`Panel` and :class:`Entry` classes.
They are automatically imported into the ``psp`` package:

.. doctest::

   >>> import psp
   >>> psp.Panel
   <class 'psp.types.Panel'>
   >>> psp.Entry
   <class 'psp.types.Entry'>

------------------------
The :class:`Panel` Class
------------------------

A panel is a pretty much just a list of entries, with the exception that
it has a date and can hold attributes.

.. class:: Panel(date)

   The ``Panel`` class.

   .. property:: date

      Date of the panel.  This is an immutable property.

   .. classmethod:: from_panel(panel)

      Create a new ``Panel`` object from attributes of ``panel``.
      Note that the new panel will hold no entries from ``panel``.


.. method:: Panel.entries()

   Return an iterator of entries.

.. method:: Panel.get_entries()

   Return a *list* copy of the entries.

.. method:: Panel.add_entry(entry)

   Add an entry to the current panel.  The ``panel`` attribute of ``entry``
   will also be set to the current panel (``self``).  If the entry belongs
   to a different entry, :meth:`Panel.remove_entry()` is called to remove
   that entry from it.

   This is a no-op if ``entry`` is already added.

.. method:: Panel.remove_entry(entry)

   Remove an entry from this panel.  A ``ValueError`` is raised if the entry
   is not in this panel.

.. method:: Panel.__contains__(self, entry)

   Return whether ``entry`` is an entry of this panel.

.. method:: Panel.count()

   Return the number of entries in this panel.

.. method:: Panel.has_entries()

   Return whether this panel has at least one entry.

.. method:: Panel.sort_entries(*, key=None, reverse=False)

   Sort the entries using ``list.sort()``.


Attributes
^^^^^^^^^^

.. method:: Panel.set_attribute(key, value)

   Set panel attribute to ``value`` under the name ``key``.


------------------------
The :class:`Entry` Class
------------------------

An entry... can do a lot of things.

There are two types of entries: text and binary.

And there are two ways data for an entry is stored: in memory or as a file.

.. class:: Entry(panel, date_time)

   The ``Entry`` class.

In addition to that the :class:`Entry` class also comes with some useful
methods.

.. method:: Entry.is_text()

   Return ``True`` if this entry can be decoded into ``str``,
   else ``False``.

There are two ways to get the underlying raw binary data, though the method
:meth:`Entry.load_data()` does it one step further by loading the data into
the object, which might be useful if you want to access the data without
reading a file every time.

.. method:: Entry.load_data()

   Load the source file into memory if it isn't loaded.
   Return the raw binary data of this entry.

.. method:: Entry.get_raw_data()

   Return the raw binary data of this entry without loading
   the source.
