.. _stringify:

==============================================
:mod:`stringify` --- Format panels and entries
==============================================

.. module:: psp.stringify
   :synopsis: Formatter stuff

This module defines classes :class:`PanelFormatter` and
:class:`EntryFormatter` for printing panels that mimics the Perspective app.

---------
Formatter
---------

.. class:: Formatter

   An `abstract base class`_ for formatter classes.

   .. _abstract base class: https://docs.python.org/3/glossary.html#term-abstract-base-class

   .. method:: format(obj)
      :abstractmethod:

      Takes an object as an argument and returns a formatted string
      representation of that object.

   .. property:: wrapper

      A wrapper object that implements a ``wrap()`` method and has a writable
      attribute ``width``.  The ``wrap()`` method takes a string and returns
      a list of lines.  Set this to ``None`` to disable line wrapping.

   .. property:: width

      An *int* representing the maximum width of each line.  Must be no less
      than 0.


---------------
Implementations
---------------

.. class:: PanelFormatter(Formatter)

   Formatter for :class:`Panel <psp.types.Panel>` objects.

   .. method:: format(panel, *, entry_formatter=None, set_options=True)

      Format a panel.

.. class:: EntryFormatter(Formatter)

   Formatter for :class:`Entry <psp.types.Entry>` objects.

   .. method:: format(entry)

      Format an entry.
