.. _main_program:

=============================
``main`` --- The main program
=============================

.. module:: psp.main
   :synopsis: The main program

This module defines a command-line interface of the ``psp`` package for

To start with... (you can do this and that with one file)

(But then you can do the same to multiple files! oh and also merging is a thing)

(Finally you can just straight up create a project :)



---------------
Basic interface
---------------

we define three commands (save from psp init)


Specifying files
^^^^^^^^^^^^^^^^

Subcommand usage
^^^^^^^^^^^^^^^^

.. code-block:: console

   $ python3 -m psp print -h
   usage: psp print [-h] [--source SOURCE] [--date DATE] [--width WIDTH]
                    [--out OUT]
                    [files ...]

   positional arguments:
     files                 backup files to load (default 'backup.json' if
                           --source is not provided); cannot be provided if the
                           --source option is present

   optional arguments:
     -h, --help            show this help message and exit
     --source SOURCE, -s SOURCE
                           a file containing source paths (relative to the file
                           itself or absolute) to all backup files on each line;
                           cannot be provided if the 'files' arguments are
                           present
     --date DATE, -d DATE  date of the panel to load (if you omit this, psp-print
                           will prompt you to enter one progressively)
     --width WIDTH, -w WIDTH
                           width of the panel to print (default is inferred from
                           your terminal size, if possible, otherwise 80)
     --out OUT, -o OUT     file name to print the panel to (default stdout)

.. code-block:: console

   $ python3 -m psp synopsis -h
   usage: psp synopsis [-h] [--source SOURCE] [--width WIDTH] [files ...]

   positional arguments:
     files                 backup files to load (default 'backup.json' if
                           --source is not provided); cannot be provided if the
                           --source option is present

   optional arguments:
     -h, --help            show this help message and exit
     --source SOURCE, -s SOURCE
                           a file containing source paths (relative to the file
                           itself or absolute) to all backup files on each line;
                           cannot be provided if the 'files' arguments are
                           present
     --width WIDTH, -w WIDTH
                           width of the synopsis being printed


Configuration file
^^^^^^^^^^^^^^^^^^


--------
Projects
--------

Rather advanced but is standalone so it's cool


tools.py
^^^^^^^^

Automatically generated

.. class:: tools.DateRequester(stuff)
   :noindex:

   sss


config.py
^^^^^^^^^

.. function:: config.get_loading_info(root)
   :noindex:

   stuff


---------------------
Python implementation
---------------------

Yeah these are cool

.. function:: main(argv)

   Evoke this without the first element of argv

   The program is evoked with::

      main(sys.argv[1:])

.. function:: create_project(project_dir)

   Create a project with cool stuff
