.. _types:

.. Using :mod:`types` links to the builtin types module so uhh don't

======================================
:mod:`psp.types` --- Important objects
======================================

.. module:: psp.types
   :synopsis: Define panel and entry classes and some others.

.. testsetup::

   from psp.types import *

This module defines the :class:`Panel` and :class:`Entry` classes, as well
as a :class:`Configurable` class that is... just there, it exists, y'know?
Like I don't know where else to put it either.


.. .. contents::
..    :local:

.. _attr_protocol:

------------------
Attribute Protocol
------------------

There is a class that :class:`Panel` and :class:`Entry` both inherit from
which defines the attribute protocol, and although this is not to be
directly used, keep in mind that you can expect these functionalities from
*both* :class:`Panel` and :class:`Entry`!

.. class:: _AttributeHolder

   Private base class for :class:`Panel` and :class:`Entry`.
   The constructor takes no positional or keyword argument.

   These are to provide a namespace for panel/entry subclasses to use;
   users should not need to call any of these methods directly.  All of
   these methods are provided to mimic a similar interface to Python's
   built-in :class:`dict` type.

   (Why didn't I just use ``__dict__`` you ask?  Well... I guess I just
   don't like exploiting Python's internal attribute representation that
   much.  I would have to teach users to use :func:`getattr` and
   :func:`setattr` to get and set attributes, and then somehow use
   ``__dict__.keys()`` to get a list of all attribute names, and probably
   if that doesn't work I'd have to use even more dunder magic and---it's
   too complicated is what I'm saying.  Plus I can't use the descriptor
   protocol for validating other attributes like :attr:`Panel.date` and
   :attr:`Entry.time` if they shared the same big namespace!)

   .. method:: get_attribute(self, name, /[, default])

      Get the attribute with *name*.
      Raise :class:`KeyError` if *name* is not an attribute.
      When *default* is provided, either as a positional or keyword
      argument, return *default* instead of raising :class:`KeyError`.
      *default* may be provided as either a positional argument or
      a keyword argument.

   .. method:: set_attribute(self, name, value, /)

      Set the attribute to *value* with *name*.

   .. method:: delete_attribute(self, name, /)

      Delete the attribute with *name*, returning the original value of
      the attribute.  Raise :class:`KeyError` if *name* is not an attribute.

   .. method:: has_attribute(self, name, /)

      Return whether the current object has an attribute with *name*.

   .. method:: get_attribute_names(self, /)

      Return a set of all attribute names; specifically, a new view of
      the internal *dict*'s keys, similar to what :meth:`dict.keys`
      returns.

   .. method:: get_attribute_items(self, /)

      Return an iterator of name-value pairs of all attributes;
      specifically, a new view of the internal *dict*'s items, similar to
      what :meth:`dict.items` returns.

   .. method:: get_attributes(self, /)

      Return a *dict* of the attributes; namely, making a shallow copy
      of the internal *dict*.

   .. method:: set_attributes(self, /, *args, **kwargs)

      Use :meth:`dict.update` to set attributes for the current object.

   .. TODO: add more words

   Comparison between two objects that implement attribute protocol:

   .. method:: __eq__(self, other)

      Return if the attributes for *self* and *other* are equal.
      Return False if *other* does not implement attribute protocol.

   .. method:: get_attributes_for_comparison()

      Return attributes used by :meth:`__eq__` to test for equality with.


Example:

>>> # Creating a panel from scratch; don't mind this part o o
>>> from datetime import date
>>> panel = Panel(date(2022, 2, 2))
>>> # Look from here:
>>> panel.set_attribute('a', 1)
>>> panel.get_attribute('a')
1
>>> panel.get_attribute('b')
Traceback (most recent call last):
  ...
KeyError: 'b'
>>> panel.get_attribute('b', 'default')
'default'
>>> panel.has_attribute('b')
False

Attributes are *not* guaranteed to be sorted, so I'm using ``sorted()``
to make these examples reproducible:

>>> panel.set_attributes({'b': 'cool', 'c': 'strings'})
>>> panel.set_attributes(d='this', e='works', f='too!')
>>> sorted(panel.get_attribute_names())
['a', 'b', 'c', 'd', 'e', 'f']
>>> for name, value in sorted(panel.get_attribute_items()):
...     print(name, value, sep=': ')
...
a: 1
b: cool
c: strings
d: this
e: works
f: too!
>>> panel.get_attributes()
{'a': 1, 'b': 'cool', 'c': 'strings', 'd': 'this', 'e': 'works', 'f': 'too!'}


-------------------
The ``Panel`` Class
-------------------

A panel, in essence, is a container of entries.  Each panel has a date
that cannot be changed once it is constructed.

.. class:: Panel(date, /)

   The panel class.  Inherits methods from the attribute protocol as
   described in :ref:`attr_protocol`.

   :param date: Date of the panel as a ``datetime.date`` object.
                Will be accessible from the :attr:`date` property.

   :example:

   >>> from datetime import date
   >>> p = Panel(date(2022, 2, 2))
   >>> p
   <Panel object on 2022-02-02>
   >>> p.date
   datetime.date(2022, 2, 2)

   .. property:: date

      Date of the panel.  This is an immutable property.

   .. classmethod:: from_panel(panel)

      Create a new panel object from the date and attributes of *panel*.
      Note that the new panel will hold no entries from *panel*.

   .. method:: copy()

      Return a copy of this panel with no entries.  Equivalent to
      ``self.from_panel(self)``.

   .. note::

      Because :attr:`date` is immutable, if you want to create a new
      panel with a changed date, you'll have to manually do that like this::

         new_panel = Panel(new_date)
         new_panel.set_attributes(old_panel.get_attributes())

      It's a bit awkward since we don't have a method like
      :meth:`datetime.datetime.replace`, but... I'm not sure if that's
      worth adding in yet.

   Since a panel is a container of entries, of course we have a ton of
   methods for accessing and modifying these entries!

   Here are the two important methods to know, although you'll probably use
   :meth:`add_entry()` most of the time.

   .. method:: Panel.add_entry(entry)

      Add *entry* to the current panel.  The :attr:`~Entry.panel` attribute
      of *entry* will also be (magically) set to the current panel
      (``self``). If the entry belongs to a different entry,
      :meth:`remove_entry` is called to remove that entry from it.

      This is a :class:`ValueError` if *entry* was already added.

   .. method:: Panel.add_entries(entries)

      Iteratively call :meth:`add_entry`.

   .. method:: Panel.remove_entry(entry)

      Remove *entry* from this panel.  A :class:`ValueError` is raised if the entry
      is not in this panel.

   .. XXX: weirdly python doesn't have method documentation for
      list.pop()...

      also there's a weird bug with putting `index=-1` here so ig...

   .. method:: pop_entry([index])

      Remove an entry from the current entry by *index* and return it.
      An :class:`IndexError` will be raised by ``list.pop()`` if
      *index* is out of bounds.  By default, pop the last entry.

   The idea is that we don't want multiple panels own the same entry, so
   an entry is automatically removed from its previous panel if it has one
   to begin with.  This is so that the ``panel`` property of entries makes
   sense, since we don't want that to be "potentially" many panels!

   Now, moving on to some accessor methods:

   .. method:: entries()

      Return an iterator of entries.

   .. method:: get_entry(index)

      Return an entry at *index*.  Works completely as
      ``self.get_entries()[index]`` (so negative indices start from
      the end).

   .. method:: get_entries()

      Return a *list* copy of the entries.

   .. method:: has_entry(obj)

      Return whether ``obj`` is an entry of this panel.
      Note that this is different from ``obj in panel.get_entries()``
      since Python's ``in`` operator compares equality and not identity.

   .. method:: count()

      Return the number of entries in this panel.

   .. method:: has_entries()

      Return whether this panel has at least one entry.

   Sometimes sorting can be convenient, hmm... who knows?

   .. method:: sort_entries(*, key=None, reverse=False)

      Sort the entries using :meth:`list.sort`.  As Python 3 guarantees,
      this method always performs a *stable* sort.

   Similar to comparing a list to another list, it is possible to compare
   a panel to another panel!

   .. describe:: p1 == p2
   .. method:: __eq__(other)

      Compare two panels and return if their date, attributes (from the
      attribute protocol), and their entries are equal (order matters).

      .. seealso::

         :meth:`Entry.__eq__` (``e1 == e2``)
            Info on entry equality rules

   Finally, as a nod to the daily ratings in the Perspective app, the
   following methods are added for accessing and modifying the *rating*
   attribute.  Although the name ``rating`` is used for the attribute
   name, you should be using these methods instead of the attribute protocol
   directly (this goes every other extension too).

   .. method:: get_rating([default])

      Get the rating for this panel.  Under the hood, this returns
      ``self.get_attribute('rating')`` where all the arguments
      and keyword arguments are passed to
      :meth:`~_AttributeHolder.get_attribute`.
      Raise :class:`KeyError` if the current panel has no rating,
      unless a default is provided, in which case that default is
      returned.

      :example:

      Usage without a default value:

      >>> from datetime import date
      >>> panel = Panel(date(2022, 2, 22))
      >>> panel.set_rating(':)')
      >>> panel.get_rating()
      ':)'

      Usage with a default value:

      >>> panel.get_rating(default=':|')
      ':)'
      >>> panel.delete_rating()
      ':)'
      >>> panel.get_rating()
      Traceback (most recent call last):
        ...
      KeyError: 'rating'
      >>> panel.get_rating(':|')
      ':|'
      >>> panel.get_rating(default=None) is None
      True

   .. method:: set_rating(rating)

      Set the rating for this panel.  Under the hood, this calls
      :meth:`~_AttributeHolder.set_attribute` with arguments
      ``('rating', rating)``.
      A :class:`TypeError` is raised if *rating* is not a *str*.

   .. method:: delete_rating()

      Delete the rating for this panel and return it.  Under the hood,
      this returns :meth:`~_AttributeHolder.delete_attribute` with
      argument ``('rating',)``.
      Raise :class:`KeyError` if the current panel has no rating.

   .. method:: has_rating()

      Return whether this panel has a rating.  Under the hood, this
      returns :meth:`~_AttributeHolder.has_attribute` with argument
      ``('rating',)``.


-------------------
The ``Entry`` Class
-------------------

An entry is either a body of text or an image in Perspective, but in the
:class:`Entry` class we generalize this to any binary file.  An entry uses
five *data attributes* (not to be confused with attributes described in
:ref:`attr_protocol`) to represent both text and binary data: *type*,
*format*, *encoding*, *raw*, and *source*.  Here's brief description of
each data attribute (sorry if they don't make sense yet):

*  *type* is a *str* representing the type of the entry.
*  *format* is a *str* representing the type of the entry.
*  *encoding* is a *str* for the encoding of raw data.
*  *raw* is a *bytes* representing the encoded text or raw binary data.
*  *source* is a path-like object for the file that stores the encoded text
   data or raw binary data.

The *encoding* and *raw* work in tandem to represent *text entries*---entries
that store a Unicode string.  Any entry whose *encoding* is not ``'binary'``
is a text entry, and :meth:`bytes.decode` will be used to decode *bytes* to
*str*.  If the *encoding* of an entry is ``'binary'``, then it is a
*binary entry*.  (This does not necessarily have to hold for subclasses, but
we'll get to that later.)

It would really suck if we had to store megabytes of images in memory,
so... aside from *raw* we also have *source*!  An entry either has *raw* or
*source*, but never both.  And when the *source* is set, :class:`Entry`
would read binary data from *source* and process it the same way it processes
*raw*.

*type* and *format* don't really do anything.  Yes, really!  They are
completely useless---jk by that I mean it's up to you to decide what
meaning they hold.  To work with file type contexts in
:mod:`filetypes <psp.filetypes>` though, you should use the ``'plain'`` type
for text entries and ``'binary'`` for binary entries (unless you register
new file types there).

.. class:: Entry(time, /, insight=False)

   The entry class.  Inherits methods from the attribute protocol as
   described in :ref:`attr_protocol`.

   :param datetime.datetime time:
                        Time of entry as an aware datetime object.
                        Will be assigned to the :attr:`time` property.
   :param bool insight: Boolean for whether this entry is an insight.
                        Will be assigned to the :attr:`insight` property.

   There are not any constraints on the values of *time* and *insight*
   when an entry is created.  However, once it is added to a panel by
   calling :meth:`Panel.add_entry`, a validation is performed with
   the panel's date (call it ``panel_date``), the :attr:`time` property
   called with the :meth:`~datetime.datetime.date` method (call it
   ``entry_date``), and the :attr:`insight` property (call it ``insight``)
   with the following rules:

   1. ``entry_date`` must be no less than ``panel_date``; and
   2. If ``insight``, then ``entry_date`` must be no less than
      ``panel_date + timedelta(days=2)``.

      *  When ``entry_date`` is a Sunday though, ``panel_date`` could
         be any one of the seven days before that Sunday.  (This is because
         Perspective lets you do weekly evaluation on every Sunday, so in
         a rare case it is possible to make an insight in less than two
         days (when you comment on the Saturday right before the Sunday).)

      *  **Implementation detail**: A :class:`ValueError` is raised only
         if the following expression is True::

            (insight
             and entry_date < panel_date + timedelta(days=2)
             and not (entry_date.weekday() == 6
                      and entry_date != panel_date))

         FYI the :meth:`date.weekday() <datetime.date.weekday>` method
         returns ``6`` for Saturday.  This ``entry_date != panel_date``
         part is a bit cheap and relies on the previous validation ensuring
         that ``entry_date >= panel_date``.  The case of ``panel_date``
         being on Sunday makes way for our exception, and the case of it
         being Monday and on is simply valid because they're at least two
         days apart.

   In layman's terms, the entry's date (in local time) should never be
   less than its panel's date.  And on top of that, if the entry is an
   insight entry, then the entry's date should never be less than two days
   after its panel's date (unless the entry is on a Sunday, then only
   one day is enough).

   The same validation is performed when either one of :attr:`time`
   or :attr:`insight` is assigned while the entry has a panel.  It is also
   performed whenever an entry is added to a new panel using
   :meth:`Panel.add_entry`.

   Here's an example of the first rule.  Since the panel's date is
   February 2, the entry's date must be February 2 or later:

   >>> from datetime import date, datetime, timezone
   >>> utc = timezone.utc
   >>> panel = Panel(date(2021, 2, 2))
   >>> entry1 = Entry(datetime(2021, 2, 1, 23, 59, tzinfo=utc))
   >>> panel.add_entry(entry1)
   Traceback (most recent call last):
     ...
   ValueError: entry time (2021-02-01 23:59:00+00:00) earlier than start of day of the parent panel (2021-02-02) in local time
   >>> # fix the time and everything should work fine from here
   >>> entry1.time = datetime(2021, 2, 2, tzinfo=utc)
   >>> panel.add_entry(entry1)
   >>> entry1.panel is panel
   True

   Note that the time zone makes no difference here.  Only the date is
   compared.

   And now here's an example of the second rule.  The entry's date now must
   be February 4 or later (not Feburary 3 because it is not a Sunday):

   >>> entry2 = Entry(datetime(2021, 2, 3, 23, 59, tzinfo=utc), True)
   >>> panel.add_entry(entry2)
   Traceback (most recent call last):
     ...
   ValueError: entry is an insight and its time (2021-02-03 23:59:00+00:00) is less than 2 days apart from the start of day of the parent panel (2021-02-02) in local time
   >>> entry2.time = datetime(2021, 2, 4, tzinfo=utc)
   >>> panel.add_entry(entry2)
   >>> entry2.panel is panel and panel.has_entry(entry2)
   True

   Now suppose the panel's date is a Saturday, say Dec 7, 2019, and you're
   commenting an insight on Sunday on that panel.  :class:`Entry` makes
   an exception for this case, allowing just one day of gap:

   >>> panel = Panel(date(2019, 12, 7))
   >>> entry = Entry(datetime(2019, 12, 8, 4, 46, tzinfo=utc), True)
   >>> panel.add_entry(entry)
   >>> entry.panel is panel and panel.has_entry(entry)
   True

   There are no other parameters for the data attributes.  Instead, set them
   with ``set_*()`` methods as I will describe in a bit.  Here are their
   default values for reference:

   *  type: ``'binary'``
   *  format: ``None``
   *  encoding: ``'binary'``
   *  raw: ``b''``
   *  source: ``None``

   Although the lack of *source* is represented as a ``None``, which you can
   obtain from :meth:`get_source` too, you cannot explicitly set it to None
   using :meth:`set_source`.  This is because as mentioned earlier, you have
   to decide to store entry data either using *raw* or using *source*, but
   not both.  That way, :meth:`get_raw_data` knows where to obtain the data
   and doesn't have to choose between two sources.  Therefore, if you want to
   unset *source*, you must use :meth:`set_raw_data` to set the raw data to
   something else.  ``entry.set_raw_data(entry.get_raw_data())`` loads all
   data into *raw* and unsets the *source*, as stupid as it looks.  The same
   thing goes for unsetting *raw* --- just set *source* to something else.

   .. property:: time

      Time of the entry.  This is always an aware datetime object.
      This is a writable property, though no changes will be made
      if the validation fails.

   .. property:: insight

      Boolean for whether this entry is an insight.
      This is a writable property, though no changes will be made
      if the validation fails.

   .. property:: panel

      The panel this entry belongs to; None if this entry does not belong
      to a panel.  This is an immutable property.

   .. method:: has_panel()

      Return ``self.panel is not None`` --- that is, True only when this
      entry belongs to a panel.

   .. classmethod:: from_entry(entry)

      Create a new entry object from the time, insight, data attributes and
      attributes of *entry*.

   .. method:: copy()

      Return a deep copy of this entry.  Equivalent to
      ``self.from_entry(self)``.

   Now, here are the getters for and related to data attributes:

   .. method:: get_type()

      Get the *type* of this entry.

   .. method:: get_format()

      Get the *format* of this entry.  None is returned if there is
      no format for this entry.

   .. method:: has_format()

      Return whether this entry has *format*.  Equivalent to
      ``self.get_format() is not None``.

   .. method:: get_encoding()

      Get the *encoding* of this entry.

   .. method:: get_source()

      Get the *source* of this entry.  None is returned if there is no
      source for this entry.

   .. method:: has_source()

      Return whether this entry has *source*.  Equivalent to
      ``self.get_source() is not None``.

   You might have realized that we are missing a getter for raw data.
   Well, that's because I didn't write one!  Instead here's something
   better:

   .. method:: get_raw_data()

      Get raw data of this entry as a *bytes*.  If data is stored in
      *raw*, then *raw* is returned.  Otherwise, the data is read from
      *source* and returned.

   So basically, it doesn't matter whether we are using *raw* or *source*.
   You can always count on :meth:`get_raw_data` to return the binary data
   for the entry!

   More often than not, however, we want to decode the raw data to retrieve
   text instead of encoded binary bytes.  Well good for you, here's another
   method that'll make your life easier!

   .. method:: get_data()

      Get text/binary data of this entry.  If this entry is a text
      entry, raw data is decoded to a string and returned.  Otherwise
      this is equivalent to :meth:`get_raw_data`.

   Whether an entry is considered a "text" entry is determined by the
   following method.

   .. method:: is_text()

      Return ``True`` if this entry can be decoded into *str*, else
      ``False``.  In default implementation, this is equivalent to
      ``self.get_encoding() != 'binary'``.

   .. note::

      Subclasses should ensure that :meth:`get_data` returns a
      *str* whenever :meth:`is_text` is True and returns a *bytes*
      whenever :meth:`is_text` is False.

   For retrieving the size of an entry:

   .. method:: get_size()

      Return the number of bytes of the raw data.

   Entry equality comparison:

   .. describe:: e1 == e2
   .. method:: __eq__(other)

      Compare two entries and return True if all of the following are
      equal:

      *  :attr:`time` (converted to UTC first)
      *  :attr:`insight`
      *  *type* (obtained from :meth:`get_type`)
      *  *format* (obtained from :meth:`get_format`)
      *  :meth:`is_text`
      *  text or binary data (obtained from :meth:`get_data`)
      *  attributes (from the attribute protocol)

      Note that if two text entries have different encodings, they will
      still compare equal as long as their decoded strings match:

      >>> from datetime import datetime, timezone
      >>> e1 = Entry(datetime(2021, 9, 15, tzinfo=timezone.utc))
      >>> e2 = e1.copy()
      >>> e1.set_data('na\u00efve', encoding='latin-1')
      >>> e2.set_data('na\u00efve', encoding='utf-8')
      >>> # although their raw data differ...
      >>> (e1.get_raw_data(), e2.get_raw_data())
      (b'na\xefve', b'na\xc3\xafve')
      >>> # ... their text data agree...
      >>> (e1.get_data(), e2.get_data())
      ('naïve', 'naïve')
      >>> # ... so the two entries are equal.
      >>> e1 == e2
      True

   Note that rich comparison is not implemented since I prefer the
   more specific comparison directly using two entries' :attr:`time`
   property.  Converting to UTC time is strongly recommended as implicitly
   time zone conversion only takes place when two datetime objects from
   different time zones are compared (i.e. intrazone comparison).

   Now that we've gone through the getters related to data attributes,
   here are the setters:

   .. method:: set_type(type)

      Set the *type* of this entry.  *type* must be a *str*.

   .. method:: set_format(format)

      Set the *format* of this entry.  *format* must be a *str* or None
      (which serves the same purpose as "deleting" the *format*).

   .. method:: set_encoding(encoding)

      Set the *encoding* of this entry.  *encoding* must be a *str*.

   .. method:: set_raw_data(raw)

      Unlike :meth:`get_raw_data`, :meth:`set_raw_data` actually sets *raw*
      to this value!  *raw* must be a *bytes*, and *source* is immediately
      set to None upon successfully setting *raw*.

   .. method:: set_source(path)

      Set the *source* of this entry.  *path* must be a path-like object.
      *raw* is immediately set to None upon successfully setting *source*.

      .. warning::

         :meth:`set_source` does not check for the existence of *path*,
         so make sure to check for potential :class:`OSError` (by trying to
         open the file in advance for example), or otherwise :meth:`get_data`
         or :meth:`get_raw_data` (and streaming methods too) might not work
         by the time you call them!

   Note that these two methods are the only way to set *raw* or *source* to
   None (assuming you're not trickily mutating private variables directly).
   This is to ensure that at least *raw* or *source* is set all the time.

   In addition to all this, we have yet another convenience method that goes
   by the name :meth:`set_data` that lets you create text entries within
   Python more easily!

   .. method:: set_data(text, type='plain', encoding='utf-8')

      Convenience method for setting this entry's data to some text.

      :param str text: The text data to set for this entry.
      :param str type: The type to set for this entry.
      :param str encoding: The encoding to encode the text with and set
                           this entry to using :meth:`set_encoding`.

      :example:

      >>> from datetime import datetime, timezone
      >>> entry = Entry(datetime(2022, 2, 22, 14, 22, tzinfo=timezone.utc))
      >>> (entry.get_type(), entry.get_encoding(), entry.get_data())
      ('binary', 'binary', b'')
      >>> entry.set_data("it's twosday innit bruv", encoding='latin-1')
      >>> (entry.get_type(), entry.get_encoding(), entry.get_data())
      ('plain', 'latin-1', "it's twosday innit bruv")

   Finally, the following methods are used to access and modify
   the question for an entry in the Perspective app under the name
   ``'question'``:

   .. method:: get_question([default])

      Get the question for this entry.  Under the hood, this returns
      ``self.get_attribute('question')`` and all the arguments and
      keyword arguments are passed to
      :meth:`~_AttributeHolder.get_attribute`.
      Raise :class:`KeyError` if the current entry has no question,
      unless a default is provided, in which case the default is returned.

      :example:

      Usage without a default value:

      >>> from datetime import datetime, timezone
      >>> entry = Entry(datetime(2022, 2, 22, tzinfo=timezone.utc))
      >>> entry.set_question('howdy')
      >>> entry.get_question()
      'howdy'

      Usage with a default value:

      >>> entry.get_question(default='are you SUS??')
      'howdy'
      >>> entry.delete_question()
      'howdy'
      >>> entry.get_question()
      Traceback (most recent call last):
        ...
      KeyError: 'question'
      >>> entry.get_question('are you SUS??')
      'are you SUS??'
      >>> entry.get_question(default=None) is None
      True

   .. method:: set_question(question)

      Set the question for this entry.  Under the hood, this calls
      :meth:`~_AttributeHolder.set_attribute` with arguments
      ``('question', question)``.
      A :class:`TypeError` is raised if *question* is not a *str*.

   .. method:: delete_question()

      Delete the question for this entry and return it.  Under the hood,
      this returns :meth:`~_AttributeHolder.delete_attribute` with argument
      ``('question',)``.  Raise :class:`KeyError` if the current entry has
      no question.

   .. method:: has_question()

      Return whether this entry has a question.  Under the hood,
      this returns :meth:`~_AttributeHolder.has_attribute` with argument
      ``('question',)``.


Streaming Interface
^^^^^^^^^^^^^^^^^^^

:class:`Entry` also offers two alternative methods to
:meth:`~Entry.get_raw_data` and :meth:`~Entry.get_data` in case data
only needs to be processed in chunks.  Instead of returning *bytes* or
*str*, these methods return file-like objects whose ``read()`` method
returns them.

.. method:: Entry.stream_raw_data()

   Similar to :meth:`get_raw_data`, return a file-like object whose
   ``read()`` method returns *bytes* of the raw data.

.. method:: Entry.stream_data()

   Similar to :meth:`get_data`, return a file-like object whose
   ``read()`` method returns the same type as what :meth:`get_data`
   returns.

Here are some examples of how :meth:`~Entry.stream_raw_data` and
:meth:`~Entry.stream_data` can be used.  Note that when the whole
buffer is read, the result is identical to :meth:`~Entry.get_raw_data`
and :meth:`~Entry.get_data`.

>>> from datetime import datetime, timezone
>>> entry = Entry(datetime(2022, 2, 22, 14, 22, tzinfo=timezone.utc))
>>> entry.set_data("it's twosday innit bruv")
>>> fp = entry.stream_raw_data()
>>> fp.read()
b"it's twosday innit bruv"
>>> fp.close()
>>> fp = entry.stream_data()
>>> fp.read()
"it's twosday innit bruv"
>>> fp.close()

These file objects do not close on their own, so remember to close them
when you're done with them!  Preferably, use a context manager to ensure
the file objects are always closed::

   with entry.stream_data() as fp:
       do_something_with(fp)
   # the file object is closed by the time we reach here

.. note::

   See :ref:`this section <0.2_panel_and_entry>` in changelog of
   release 0.2 for a guide on how to export entries to a file.


-----------------
Extension Support
-----------------

Panel and entry can be extended by simply subclassing :class:`Panel` or
:class:`Entry`.  No registration is required, though you can define an
*extension name* to make introspection easier by providing the ``extname``,
like this::

   class FooEntry(Entry, extname='foo'):
       __slots__ = ()

   class FooPanel(Panel, extname='foo'):
       __slots__ = ()

The extension name may not be changed after that, and its name can be
accessed by calling :meth:`Entry.get_extension_name()
<psp.types.Entry.get_extension_name>` and :meth:`Panel.get_extension_name()
<psp.types.Panel.get_extension_name>`:

.. testsetup:: ext

   from psp.types import Entry, Panel

   class FooEntry(Entry, extname='foo'):
       __slots__ = ()

   class FooPanel(Panel, extname='foo'):
       __slots__ = ()

.. doctest:: ext

   >>> FooEntry.get_extension_name()
   'foo'
   >>> FooPanel.get_extension_name()
   'foo'

If ``extname`` is not provided, ``cls.__name__`` (``cls`` is the subclass)
is used instead:

>>> class BarEntry(Entry):
...     __slots__ = ()
...
>>> class BarPanel(Panel):
...     __slots__ = ()
...
>>> BarEntry.get_extension_name()
'BarEntry'
>>> BarPanel.get_extension_name()
'BarPanel'

You might be tempted to call ``Panel.get_extension_name()`` or
``Entry.get_extension_name()``, but don't!  These base classes are not
supposed to be used as extensions and you'll get an ``AttributeError``
that way.

.. classmethod:: Panel.get_extension_name()

   Return extension name for the current panel class.

.. classmethod:: Entry.get_extension_name()

   Return extension name for the current entry class.


--------------------------
The ``Configurable`` Class
--------------------------

Lastly we have a class that is useful for defining user options.  Why?
Well, because otherwise we would have at least three classes that have
the same exact code!  So you clearly know it could be done when you
literally copy-and-paste more than 50 lines of code, right?

.. class:: Configurable

   Base class for classes that have options.

   The class itself doesn't have an option registry, but subclasses will.
   And although there are no abstract methods to implement, you should not
   use this class directly.  For the sake of demonstration I will be using
   this subclass:

   >>> class ConfigSubclass(Configurable):
   ...     __slots__ = ()
   ...
   >>> ConfigSubclass.get_registered_option_names()
   dict_keys([])

   The example above calls the :meth:`get_registered_option_names` class
   method that retrieves the option names that have been registered.
   Below we will first look at all the class methods concerning
   registration.

   .. classmethod:: add_option(name, default, hook=None)

      Register an option named *name* with a default value of *default*.
      An optional *hook* can be supplied as a callback function, which will
      be called every time the user attempts to set the option.  (See
      :meth:`set_option` on how the *hook* is used.)

      :class:`ValueError` is raised if *name* is already registered.

   .. classmethod:: is_option_registered(name)

      Return whether the option has been registered.

   .. classmethod:: remove_option(name)

      Unregister an option named *name*.  Return a tuple of the default
      value and the hook function on success (if the option does not have
      a hook, None takes the place of the hook).  :class:`KeyError` is
      raised if *name* is not registered.

   The class method we just looked at is used for obtaining all the options:

   .. classmethod:: get_registered_option_names()

      Return a set of all registered option names.

   Each time a new class is created, the option names, paired with a deep
   copy of the default values, are used to initialize an internal option
   *dict*.  No option can be deleted after the object is instantiated, and
   users may not add any extra options, only overwrite existing ones.
   More on that later, but first here are the methods concerning the
   internal option *dict*:

   .. method:: set_option(name, value)

      Set the option with *name* to *value*.  Raise :class:`ValueError`
      if *name* is not an existing option for this instance.

      If a *hook* is registered in :meth:`add_option` for *name*, it is
      called with arguments ``(self, name, value)`` (``self`` is the
      current instance) and its return value is used instead of *value*.

   .. method:: get_option(name)

      Get the value of the option with *name*.  Raise :class:`KeyError`
      if *name* is not an existing option for this instance.

   .. method:: has_option(name)

      Return whether this instance has option named *name*.

   .. method:: configure(**kwargs)

      Set option with the name and value of every keyword argument.
      This method calls :meth:`set_option` whether you like it or not.

   .. method:: get_option_names()

      Return a set of all option names for this instance.

Most of the time you won't want to change options once they are defined,
but here are the rules for your reference anyways.

An important thing to note is that while we use the class to *define*
options that can be used, the options themselves are *stored* in the
instance.  That is, if we use a class to demonstrate:

>>> class Config(Configurable):
...     __slots__ = ()
...
>>> Config.add_option('foo', 42)

Currently ``Config`` has one option "foo", so every instance created from
there on will have the same one option too:

>>> a = Config()
>>> sorted(a.get_option_names())
['foo']

But now if we add another option "bar", every instance created from there on
will have both "foo" and "bar" as options:

>>> Config.add_option('bar', 17)
>>> b = Config()
>>> sorted(b.get_option_names())
['bar', 'foo']

The instance we created earlier, however, isn't affected.

>>> sorted(a.get_option_names())
['foo']

And as described in :meth:`~Configurable.set_option`, an option is
considered invalid in the scope of an instance, *not* the options
the class defines:

>>> a.set_option('bar', 420)
Traceback (most recent call last):
  ...
ValueError: invalid option name for Config: 'bar'
>>> b.set_option('bar', 420)
>>> b.get_option('bar')
420

And of course, once an instance is created, there's nothing you can do to
change the options.
At least, not with :meth:`~Configurable.remove_option`.

>>> Config.remove_option('bar')
(17, None)
>>> b.set_option('bar', 69)
>>> b.get_option('bar')
69

On the other hand, option hooks are stored in *classes*, so option checking
may only take place if the instance's class defines it.  As another example,
let's make another subclass and add an option with a hook:

>>> class ConfigAgain(Configurable):
...     __slots__ = ()
...
>>> def checker(self, name, value):
...     print(f'option hook called with {(name, value)}!')
...     return value
...
>>> ConfigAgain.add_option('foo', 42, checker)

This time, notice how a change in the behavior of ``a.set_option()`` is
changed because ``ConfigAgain`` is no longer defined:

>>> a = ConfigAgain()
>>> a.set_option('foo', 420)
option hook called with ('foo', 420)!
>>> ConfigAgain.remove_option('foo')
(42, <function checker at 0x...>)
>>> a.set_option('foo', 69)
>>> # Nothing happens...

Finally, inheritance.  You guys probably wonder how this would turn out if
you subclassed something configurable and has options.  Well here's something
good to know:

*  Each subclass has their own separate option registry; and
*  Options from base classes are merged from right to left.

.. XXX uhh is this the proper term for multiple inheritance order

For instance, say you have a class like this:

>>> class A(Configurable):
...     __slots__ = ()
...
>>> A.add_option('foo', 17)
>>> sorted(A.get_registered_option_names())
['foo']

Then if you create subclasses, each subclass would always obtain a copy of
the options in their parent class.

>>> class Child(A):
...     __slots__ = ()
...
>>> sorted(Child.get_registered_option_names())
['foo']

Adding an option in the subclass does not affect the parent class:

>>> Child.add_option('bar', 29)
>>> sorted(Child.get_registered_option_names())
['bar', 'foo']
>>> sorted(A.get_registered_option_names())
['foo']

And when you have multiple base classes, options are merged from
right to left.  For example, let's say you have another class that
implements some options that are somewhat the same:

>>> class B(Configurable):
...     __slots__ = ()
...
>>> B.add_option('foo', 42)

And for demonstration's sake, let's add an option unique to ``A``:

>>> A.add_option('baz', 12)  # A now has foo=17 and baz=12

Then

>>> class ChildA(A, B):
...     __slots__ = ()
...
>>> class ChildB(B, A):
...     __slots__ = ()
...
>>> def get_options(cls):
...     instance = cls()
...     return sorted((name, instance.get_option(name))
...                   for name in instance.get_option_names())
...
>>> get_options(ChildA)
[('baz', 12), ('foo', 17)]
>>> get_options(ChildB)
[('baz', 12), ('foo', 42)]

As you can see, since the "foo" option is present in class ``A`` and
class ``B``, ``ChildA`` derives the default value ``17`` from ``A`` since
it is the leftmost class that defines the option, and ``ChildB`` derives
``42`` from ``B`` since it is the leftmost class there.
(I hope I made myself clear there...)
