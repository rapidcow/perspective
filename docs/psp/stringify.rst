.. _stringify:

==============================================
:mod:`stringify` --- Format panels and entries
==============================================

.. module:: psp.stringify
   :synopsis: Formatter stuff

This module defines classes :class:`PanelFormatter` and
:class:`EntryFormatter` for printing panels that mimics the interface
from the app Perspective.

---------
Formatter
---------

.. class:: Formatter

   An `abstract base class`_ for formatter classes.

   .. _abstract base class: https://docs.python.org/3/glossary.html#term-abstract-base-class

   .. method:: __init__(self, width=80, wrapper=None, **options)

      Initialize formatter.

      .. TODO Talk about width and wrapper and instantation stuff

      The options are passed on to :meth:`configure`.

   .. method:: configure(**options)

      Configure options.  The following is a table of all options:

      +--------------------+---------------------------------+----------+----------------+
      | Option             | Description                     | Type     | Default        |
      +--------------------+---------------------------------+----------+----------------+
      | ``indent``         | String to prepend to each line. | *str*    | ``''``         |
      +--------------------+---------------------------------+----------+----------------+
      | ``strlen``         | Function that takes a *str*     | callable | ``len``        |
      |                    | and returns it length.          |          |                |
      +--------------------+---------------------------------+----------+----------------+
      | ``line_callback``  | Function that is called on      | callable | ``str.rstrip`` |
      |                    | each line.                      |          |                |
      +--------------------+---------------------------------+----------+----------------+

   .. method:: format(obj)
      :abstractmethod:

      Takes an object as an argument and returns a formatted string
      representation of that object.

   .. property:: wrapper

      A wrapper object that implements a ``wrap()`` method and has a writable
      attribute ``width``.  The ``wrap()`` method takes a string and returns
      a list of lines, each with length no more than ``width``.  Set this to
      ``None`` to disable line wrapping.

   .. property:: width

      An *int* representing the maximum width of each line.  Must be no less
      than 0.

   Protected attributes for subclassing:

   .. attribute:: _all_options

      A *set* of all option names.  Subclasses should update this so that
      :meth:`configure` knows what options are valid and what aren't.

   .. attribute:: _options

      A *dict* of the option names and values.

   Protected methods:

   .. explain: wrapping = taking a string and returning a list of lines

   .. method:: _is_wrapping_disabled()

      Return whether text wrapping will be used.

   .. method:: _wrap(text)

      Low-level wrapping.

   .. method:: _wrap_paragraph(text, *, prefix='', fillchar=' ', return_empty=False)

      Wrap left-aligned text.

   .. method:: _center_paragraph(text, *, fillchar=' ', return_empty=False)

      Wrap centered text.

   .. I don't plan to document about _center_line()... since it's not
      really something you would want to use when you have _center_paragraph()
      already.

.. TODO: Give subclass examples


---------------
Implementations
---------------

.. class:: PanelFormatter(Formatter)

   Formatter for :class:`Panel <psp.types.Panel>` objects.

   .. TODO: options
   ..       and doctest examples!!

   .. method:: format(panel)

      Format a panel.

   .. method:: set_entry_formatter(formatter)

      Set the entry formatter for :meth:`format` to use.

   .. method:: get_entry_formatter(formatter)

      Get the entry formatter for :meth:`format` to use.
      If :meth:`set_entry_formatter` was never called, an
      :class:`EntryFormatter` instance is automatically created.

   .. method:: configure_entry_formatter(entry_formatter, panel)

      When :meth:`format` is called, its argument ``panel`` as well
      as the entry formatter are passed to this function.
      Options to keep the entry formatter consistent with the panel
      are set by default.

      .. TODO: Explain what options are set exactly (like the time
         zone and all those weird options passed to ``configure()``)

.. class:: EntryFormatter(Formatter)

   Formatter for :class:`Entry <psp.types.Entry>` objects.

   .. TODO: options
   ..       and doctest examples too!!

   .. method:: format(entry)

      Format an entry.
