.. _serializers_text:

======================================================
:mod:`psp.serializers.text` --- Simple text processors
======================================================

.. module:: psp.serializers.text
   :synopsis: Simple text processors

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

into a :class:`dict` object that can be parsed by
:meth:`~psp.serializers.json.JSONLoader.load_data`
like this:

.. code-block:: json

   {
     "tz": "+08:00",
     "paths": [
       ".",
       "doc"
     ]
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


--------------
How this works
--------------

List out all the keywords here


-------
Classes
-------

.. note::

   :mod:`shlex` is used so know that

   The ``punctuation_chars`` parameter of the :class:`~shlex.shlex`
   constructor only works for Python 3.6+ so uh know that I guess


.. class:: TextLoader(**options)

   .. method:: load(fp)

      Same as :meth:`loads`, except the text is read from file object.

   .. method:: loads(s)

      Plain text ``s`` to JSON object

      ehh I don't know


.. class:: TextDumper(**options)

   .. method:: dump(fp)

   .. method:: dumps(obj, fp)
