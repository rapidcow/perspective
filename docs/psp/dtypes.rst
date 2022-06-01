.. _datatypes:

======================================================
:mod:`datatypes` --- File type and extension inference
======================================================

.. module:: psp.datatypes
   :synopsis: Inference rules for file types, their text/binary nature, and 
              their extensions

The main purpose of this module is to handle type inferences.  For example,
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
:mod:`psp.processors.json_processor` module.  Here I will only describe
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
