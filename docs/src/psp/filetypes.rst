.. _filetypes:

============================================
:mod:`psp.filetypes` --- Defining file types
============================================

.. module:: psp.filetypes
   :synopsis: File type mayhem

.. this is a very interesting module but unfortunately i don't have time
   to write anything as you can see :( (i swear i'm not mimicking Fermat)

.. function:: set_context(context)

   Set the current file type context.  *context* be a
   :class:`FileTypeContext` instance.

.. function:: get_context()

   Get the current file type context.  If no context was set for this
   thread (?), a new :class:`FileTypeContext` is created, set, and returned.

.. function:: local_context(context=None)

   A context manager that temporarily sets the file type context.
   If *context* is None, the context is retrieved from :func:`get_context`.
   Return the current context on ``__enter__``.

.. class:: FileTypeContext

   Cool context objects wow (*totally* not a ripoff of
   :class:`decimal.Context`!!1!)

   .. method:: copy()

      Return a copy of the current context instance.


.. XXX old thing from dtypes.rst

.. The main purpose of this module is to handle type inferences.  For example,
   if you write

   .. code-block:: json

      {
          "time": "14:29",
          "type": "markdown",
          "input": "1.txt"
      }

   in your entry of a backup file, you would want the loader to know that
   this is text and not pure binary data is stored, whereas if you write

   .. code-block:: json

      {
          "time": "15:29",
          "input": "some_photo.jpg"
      }

   you would want the loader to know that this is pure binary data and is
   also a JPEG file.  This module helps to do exactly that, but the exact
   implementation inference rules are written in the
   :mod:`psp.serializers.json` module.  Here I will only describe
   the functionalities of this module.


   .. testsetup::

      from psp.datatypes import *


   ------------
   Registration
   ------------

   Lots and lots of names, common or whatnot, and you can check them by
   running the :func:`has_type()` function.

   .. function:: register_data_type(name, is_text, exts, aliases=None)

      Register a data type of with *name*, a string that has
      underscore-separated names (like ``stuff_xml`` and ``big_cow``).


   .. function:: delete_data_type(name)

      Delete the data type with *name*.  ``ValueError`` is raised
      if the name was not registered.


   ----------------
   Lookup Functions
   ----------------

   On a technical note, most of the lookup functions here are cached with
   ``functools.lru_cache()``.

   .. function:: has_type(name)

      Return whether the given type ``name`` has been registered.

      Example:

      .. doctest::

         >>> has_type('markdown')
         True
         >>> has_type('among_us')
         False
