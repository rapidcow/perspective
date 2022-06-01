.. _installation:

------------
Installation
------------

Run the following commands in your terminal/shell/whatever:

.. code-block:: shell

   git clone https://github.com/rapidcow/perspective.git
   cd perspective/src
   python3 -m pip install .

where ``python3`` is the name of your Python 3 interpreter.

It might be helpful to use a `virtual environment`_. In that case
you can instead run

.. code-block:: shell

   git clone https://github.com/rapidcow/perspective.git
   cd perspective
   # Create and activate a virtual environment
   python3 -m venv .env
   # Activate the environment --- depends on your platform!
   source .env/bin/activate
   # Now install the library
   cd perspective/src
   pip install .

See the above link for how to activate a virtual environment.

.. _virtual environment: https://docs.python.org/3/library/venv.html
