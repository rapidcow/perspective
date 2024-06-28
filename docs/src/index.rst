.. _home:

======================================
The Perspective Journal documentation!
======================================

Welcome!  This is a pure Python library providing backup utility for the
iOS journaling app `Perspective`_, as well as backing up and processing
diaries in general!

.. _Perspective: http://blinky.co/perspective_app/


Installation
------------

The package requires Python 3.8 or later installed on your machine
(namely it uses :meth:`datetime.datetime.fromisoformat` and
other new Python things I can't remember).
To install, run the following commands in your terminal:

.. code-block:: sh

   git clone https://git.rapidcow.org/perspective.git
   # perspective is no longer on github - but it *is* on codeberg!
   git clone https://codeberg.org/rapidcow/perspective.git
   python3 -m pip install perspective/src

or one-liners:

.. code-block:: sh

   python3 -m pip install git+https://git.rapidcow.org/perspective.git@v0.1#subdirectory=src
   python3 -m pip install git+https://codeberg.org/rapidcow/perspective.git@v0.1#subdirectory=src

Remember to replace ``python3`` with the name of your Python 3 interpreter!
(``pip install`` / ``pip3 install`` also work - sometimes.)

To uninstall the package name you to specify is perspe, e.g.
``python3 -m pip uninstall perspe``


Quick start
-----------

Read these first because uh I give examples

.. toctree::
   :maxdepth: 1

   intro/about.rst
   tutorials/index.rst


Technical stuff
---------------

The actual documentation but might be too boring to read

.. toctree::
   :maxdepth: 1

   changelog/index.rst
   contrib.rst
   basicproc/zero.rst
   psp/index.rst
   struct/index.rst


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
