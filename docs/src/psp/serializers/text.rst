.. _serializers_text:

=============================================================
:mod:`psp.serializers.text` --- Simple text backup processors
=============================================================

.. module:: psp.serializers.text
   :synopsis: Simple text backup processors

I can't emphasize how useful `plainconv.py`_ has been to me, given how
in the past directly writing JSON was the only way I could back up and
write new entries.  And indeed, this is the only feasible way I can
make creating and editing entries remotely user-friendly, since you'd
have to specify *so* much with :class:`~psp.serializers.json.JSONLoader`.

.. _plainconv.py: https://gist.github.com/rapidcow/c2dda740d428db832b91b82e265a3b01/

So, what this module does is essentially what `plainconv.py`_
does --- converting from a plain text format like this:

.. code-block:: text

   # shell-like comments are supported! :D
   YEAR 2023           # default year
   TIME ZONE +08:00    # optional stuff
   PATHS [".", "doc"]

   DATE Mar 14 :(
   TIME 3:29 pm
   <<< markdown
   this  is an  entry with   *s t u f f*
   # this is not a comment
   >>>

   TIME Mar 15 18:20
   QUESTION what are you
   INPUT someVileFile.txt (plain)

   DATE Feb 14 2022
   INSIGHT Mar 15 2023 5:17 pm
   <<<
   oh
     and
       many lines too
   >>>

into a :class:`dict` object that can be parsed by |json_load|
like this:

.. code-block:: json

   {
     "tz": "+08:00",
     "paths": [
       ".",
       "doc"
     ],
     "year": "2023",
     "data": [
       {
         "date": "2023-03-14",
         "rating": ":(",
         "entries": [
           {
             "time": "15:29",
             "type": "markdown",
             "data": "this  is an  entry with   *s t u f f*\n# this is not a comment"
           },
           {
             "date-time": "2023-03-15 18:20",
             "question": "what are you",
             "type": "plain",
             "input": "someVileFile.txt"
           }
         ]
       },
       {
         "date": "2022-02-14",
         "entries": [
           {
             "date-time": "2023-03-15 17:17",
             "insight": true,
             "data": "oh\n  and\n    many lines too"
           }
         ]
       }
     ]
   }

And the other way around too!  (If necessary, that is...)


------------------
The technicalities
------------------

The text format is processed on a per-line basis, where special
words called *keywords* at the beginning of a line determine what
the parser should do.
Spaces are always ignored, and lines are split into chunks of
smaller words called *tokens*, akin to shell parsing
rules.  (Keywords are tokens immediately.)
Keywords are case-insensitive too (i.e. always converted to
uppercase letters using :meth:`str.upper`).
Therefore, declaring a panel and an entry like this

.. code-block:: sh

   DATE March 03 2023
   TIME 12:30

is equivalent to this, since they produce the same tokens:

.. code-block:: sh

   daTe 'march'  03  2023
   TimE   12":"30

The reason for quotes to be included in the syntax is similar
to why you might want to quote in a shell: if you intend to
include spaces in an argument and not have the processor split
on whitespace, quote it like so:

.. code-blocks: sh

   # this is one token, rather than three
   DATE "march 03 2023"
   # spaces are preserved verbatim
   DATE " march  03  2023 "

(Again, comments are valid and completely ignored;
they start with a ``#`` character.)


Introduction to the formal syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The general structure is as follows:

*  A panel is declared with either one of the keywords
   ``DATE`` and ``PANEL``, followed by the date of the panel
   (optionally the rating too):

   .. code-block:: sh

      # creates a panel on 2023-04-20
      DATE Apr 20 2023
      # same panel but with rating :(
      DATE Apr 20 2023 :(

   .. ) this is for vim highlighting, sorry

   This keyword always takes precedence, in that an entry is
   always terminated and a new panel is always started
   (unless inside a ``<<< ... >>>`` block).

*  An entry is declared with either one of the keywords
   ``ENTRY`` or ``TIME``, followed by the time of the panel.
   An entry is started / terminated upon finding any one of
   these keywords.

*  An *insight* entry is declared with ``INSIGHT`` or
   ``INSIGHT ENTRY`` (two tokens).  The same logic above
   applies.

*  Before encountering any panel or entry keyword, any keyword
   is recognized as a *top-level attribute*, much like the ones
   with JSON archives.  (This is mostly an effort serialization
   with this format possible...)

As an example, here's how the panel and entry keywords divide up
such plain text format:

.. code-block:: text

   PATH ...    # \
   TZ ...      #  | top-level
   desc ...    # /

   DATE ...    # ------------\
   RATE ...    #              \
   ATTR ...    #              |
               #              |
   TIME ...    # \            |
   TYPE ...    #  \           |
   <<<         #  |           | panel
   [...]       #  | entry     | #1
   >>>         #  | #1        |
   ATTR ...    #  /           |
               # /            |
   TIME ...    # \            |
   TYPE ...    #  \ entry     |
   INPUT ...   #  / #2        /
               # /           /
   DATE ...    # ------------\
   ...         #              \
   ...         #              | panel #2...

*  The content of an entry (corresponding to the "data" tag)
   is fenced by ``<<<`` and ``>>>`` appearing on a separate line.
   The number of ``<`` may vary from one to as many as you wish,
   but the number of terminating ``<`` must match that number:

   .. code-block:: text

      DATE Apr 21 2023
      TIME 22:40
      <<<<<
      content began with five <'s, so we'd expect five >'s
      not this:
      >>>
      or any this:
      >>>>>>>>
      >>>>> i like trains
      but precisely, this:
      >>>>>

   Content is read in verbatim, *including* more than one whitespace
   characters (space/tab), escape (``\\``) and comment (``#``)
   characters, line-terminating characters (``\r\n``), and
   as well as ``<<<`` and ``>>>`` themselves (this is one reason
   for allowing varying lengths!)

*  Besides these guys, there are panel attributes and entry
   attributes.  Parsing of panel attributes ends as soon as an
   entry is begun by a keyword like ``TIME``.  Here is an
   example of some of the common ones:

   .. code-block:: text

      DATE APRIL 1 2023
      # panel attributes
      RATING :D
      ATTR {
        "custom-attribute": "foo!"
      }

      TIME 12:30
      # entry attributes
      TYPE markdown
      FORMAT pandoc
      QUESTION How was your day?
      <<<
      ok!
      >>>
      ATTR {
        "custom-attribute": "bar!"
      }

   which produces this:

   .. code-block:: json

      {
        "data": [
          {
            "date": "2023-04-01",
            "rating": ":D",
            "custom-attribute": "foo!",
            "entries": [
              {
                "time": "12:30",
                "type": "markdown",
                "format": "pandoc",
                "question": "How was your day?",
                "data": "ok!\n",
                "custom-attribute": "bar!"
              }
            ]
          }
        ]
      }

   Every attribute here should be self-explanatory
   (note that more than one whitespace is always ignored
   unless you quote them like so: ``"hello  world"``).
   ``ATTR`` is basically a hopeless attempt at converting
   anything that isn't recognized by the parser by default.


Definition
~~~~~~~~~~

String and JSON arguments (ye important)


-------
Classes
-------

.. note::

   This module depends on :mod:`shlex` library for Python 3.6+
   (the ``punctuation_chars`` argument)...

   ...except it doesn't.  Due to internal hacks I actually had
   to copy the source code of :class:`shlex.shlex`, so maybe
   it'll work in older verions too.


.. XXX i think composition isn't needed...? (it'd get confusing)
   we can just do loader.load_data(text_loader()) or something...

.. class:: TextLoader(**options)

   Text backup file loader.
   Keyword arguments are passed to the :meth:`configure` method.

   .. method:: configure(**options)

      Configure options, inherited from |configure|.

   .. method:: load(fp)

      Convert a text backup into its JSON-equivalence that can be
      parsed by :class:`~psp.serializers.json.JSONLoader`.

   .. method:: loads(s)

      Same as :meth:`load`, except reads from the content of
      a string.


This class has not yet been implemented

.. class:: TextDumper(**options)

   Text backup file dumper.
   Keyword arguments are passed to the :meth:`configure` method.

   .. method:: configure(**options)

      Configure options, inherited from |configure|.

   .. method:: dumps(obj, fp)

   .. method:: dump(fp)

.. |configure| replace:: :meth:`Configurable.configure() <psp.types.Configurable.configure>`
.. |json_load| replace:: :meth:`JSONLoader.load_data() <psp.serializers.json.JSONLoader.load_data>`
