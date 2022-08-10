=======================================
How to back up entries from Perspective
=======================================

:Author: rapidcow <thegentlecow@gmail.com>
:Date: May something, 2022
:Video: I haven't recorded it lol

.. contents::
   :local:


.. Remember: TWO SPACES BEFORE EACH HEADER!!

Setting up
----------

Backup process
--------------

Using the main program
----------------------

Checking for errors
~~~~~~~~~~~~~~~~~~~

Basic configuration
~~~~~~~~~~~~~~~~~~~

Some configurations you might find helpful...

A basic template to work with (this is used the default)::

   from psp.processors.json_processor import JSONLoader
   from psp.stringify import PanelFormatter


   class BackupLoader(JSONLoader):
       def configure(self, **kwargs):
           super().configure(**kwargs)

       def load_json(self, file, encoding):
           with open(file, encoding=encoding) as fp:
               return json.load(fp)

       def load_all(self, data):
           return super().load_data(data)

       def load_single(self, data, date):
           return super().load_data(data, date=date)


   class PanelPrinter:
       def __init__(self, width):
           self.formatter = PanelFormatter(width)

       def print(self, panel, file):
           print(self.formatter.format(panel), file=file)

In the configuration file you only have to define classes that you
want to override.  Run

.. code-block:: sh

   python -m psp -c=config.py print backup.json

to run the *psp print* command with your configuration file.
(Replace ``config.py`` with the path to your file.)

24-hour format::

   from psp.stringify import PanelFormatter

   class PanelPrinter:
       def __init__(self, width):
           self.formatter = PanelFormatter(width)
           self.formatter.configure(time_format='24 hour')

       def print(self, panel, file):
           print(self.formatter.format(panel), file=file)

Loading with ``BigLoader``... just replace ``JSONLoader`` in the
above code with ``BigLoader`` after importing using ::

   from psp.extensions.bigentry import BigLoader


Helpful tools I use
-------------------

``plainconv.py``
~~~~~~~~~~~~~~~~

``panel2html.py``
~~~~~~~~~~~~~~~~~
