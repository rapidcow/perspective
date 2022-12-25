============
Contributing
============

TODO: Bugs?  Pull requests?

Setup
-----

The source code, documentation, as well as test cases, are all on `GitHub`_.
To start messing things around, I recommend cloning the repo, create a
virtual environment and install it there:

.. code-block:: sh

   git clone https://github.com/rapidcow/perspective.git
   python -m venv .env
   # Activate the virtual environment, e.g. for Bash it looks like this:
   source .env/bin/activate
   # Install in editable mode (so that any changes you make here in the
   # source code will automatically work!)
   cd perspective/src
   pip install -e .

.. _GitHub: https://github.com/rapidcow/perspective


Code guidelines
---------------

Good code is hard to write, and I get that.  It's hard to even say that
I know what I am doing either!  Despite this, I will still list out a few
things I would like us to follow:

*   Adhere to `PEP 8`_ whenever possible.  This includes: proper naming
    style (``like_this`` for variables and ``LikeThis`` for classes),
    use a leading underscore ``_like_this`` for private methods), four-space
    indentation, adding spaces for readability (except in keyword arguments),
    using Python idioms, using comments to explain the code when the reader
    might not get the purpose of the code right away.
*   Above all else, be consistent!
*   Docstrings aren't a must but are most certainly welcomed :D

.. _PEP 8: https://peps.python.org/pep-0008/


Documentation
-------------

Read ``docs/README.md`` in the repository.
