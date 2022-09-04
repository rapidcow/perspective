.. _what is this?:

-------------
What is this?
-------------

The Perspective library is one of my personal coding projects which I
decided to upload to `a GitHub repository
<https://github.com/rapidcow/perspective>`_ due to how useful it has become
to me.  This right here is a little documentation for all the gibberish
source code and stuff I have.

As for basicproc.py_, well, you can say it was a prototype of the library.
It had all the core concepts like time zone, lookup paths, and the keys,
except too many functionalities are condensed into one single class.
Over time it grew larger (> 1000 lines) and adding new features like
exporting entries and formatting different time zones was impossible without
terrible exploitation of the syntax, so the Perspective library was made to
replace it and extend the features from there on.

.. _basicproc.py: https://gist.github.com/rapidcow/a0490a57965061ae06e5c43b2c97e46c

I chose to include it not because of its practical uses but the ideas I've
established while designing it, which more or less are copied directly into
the Perspective library.  But to be honest, I think I'll have to sort out
these things before I can call it final... (haha if only I had time to XD)

There are two objectives I would like to achieve with this library:

*  A tool to help back up entries from the iOS journaling app Perspective
   (and diaries in general!)
*  A programming interface for doing fancy stuff to the backup files


Okay, that's cool and all, but what *can* it do?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

I'm glad you asked!  It's hard for me to show it to you guys, but I'll
try...

The ``psp`` package operates on what are called *backup files* as basic
building blocks, which are essentially JSON files with a special format.
Here's what one might look like:

.. code-block:: json

   {
     "tz": "+08:00",
     "data": [
       {
         "date": "2020-02-02",
         "entries": [
           {
             "time": "06:00",
             "data": "Hello world!"
           },
           {
             "date-time": "2020-02-03 20:00",
             "data": "Another entry from a different date!"
           }
         ]
       }
     ]
   }

Save the above file as ``backup.json`` to run these examples:

.. See newtests/test_main.py for test code so that I make sure these
   examples don't flunk :DDDD

*  A main program that prints out a panel on a specific day from a
   backup file:

   .. code-block:: console

      $ python3 -m psp print backup.json --date 2020-02-02 -w 65
      =================================================================
                          Sunday, February 2, 2020


      6:00 AM
        Hello world!

      Feb  3   8:00 PM
        Another entry from a different date!
      =================================================================

   Or maybe sometimes you forgor the date 💀 (don't worry, I never
   remember them either)

   .. code-block:: console

      $ python -m psp print backup.json -w 65
      Select one year from the years below:
         2020
      Year: 2020

      Select one month from the months of 2020 below:
         Feb
      Month: 2

      Select one day from February 2020 below:
          2
      Day: 2
      =================================================================
                          Sunday, February 2, 2020


      6:00 AM
        Hello world!

      Feb  3   8:00 PM
        Another entry from a different date!
      =================================================================

   Works in a similar way for multiple backup files too!

*  An API that can do the same thing (but more flexible)::

      from psp.stringify import print_panel
      from psp.processors import load_json

      panel = load_json('backup.json', date='2020-02-02')
      print_panel(panel, 65)                          # default 12-hour format
      print_panel(panel, 65, time_format='24 hour')   # 24-hour format

*  Time zone!  Despite ``print_panel()`` hiding it whenever it can, time is
   always internally stored as aware :class:`~datetime.datetime` objects.

   .. testsetup::

      from psp.stringify import print_panel
      from psp.processors import load_json
      from io import StringIO

      panel = load_json(StringIO("""\
          {
            "tz": "+08:00",
            "data": [
              {
                "date": "2020-02-02",
                "entries": [
                  {
                    "time": "06:00",
                    "data": "Hello world!"
                  },
                  {
                    "date-time": "2020-02-03 20:00",
                    "data": "Another entry from a different date!"
                  }
                ]
              }
            ]
          }
          """), date='2020-02-02')

   >>> from psp.timeutil import parse_timezone
   >>> if True:
   ...     print('=' * 38)
   ...     print_panel(panel, 38, infer_time_zone=False)
   ...     print('=' * 38)
   ...
   ======================================
          Sunday, February 2, 2020
   <BLANKLINE>
   <BLANKLINE>
   6:00 AM [+08:00]
     Hello world!
   <BLANKLINE>
   Feb  3   8:00 PM [+08:00]
     Another entry from a different date!
   ======================================
   >>> # Let's change up the time zone of the second entry...
   >>> pst = parse_timezone('-08:00')
   >>> panel.get_entry(1).time = panel.get_entry(1).time.astimezone(pst)
   >>> if True:
   ...     print('=' * 38)
   ...     print_panel(panel, 38, infer_time_zone=False)
   ...     print('=' * 38)
   ...
   ======================================
          Sunday, February 2, 2020
   <BLANKLINE>
   <BLANKLINE>
   6:00 AM [+08:00]
     Hello world!
   <BLANKLINE>
   Feb  3   4:00 AM [-08:00]
     Another entry from a different date!
   ======================================
   >>> # Time zone coersion is also possible...
   >>> from datetime import timezone
   >>> if True:
   ...    print('=' * 38)
   ...    print_panel(panel, 38,
   ...                time_zone=timezone.utc,
   ...                coerce_time_zone=True)
   ...    print('=' * 38)
   ...
   ======================================
          Sunday, February 2, 2020
   <BLANKLINE>
   <BLANKLINE>
   Feb  1  10:00 PM
     Hello world!
   <BLANKLINE>
   Feb  3  12:00 PM
     Another entry from a different date!
   ======================================

*  Basic configuration of the output:

   .. code-block:: console

      $ python -m psp -c config.py print backup.json --date 2020-02-02 -w 65
      +---------------------------------------------------------------+
      |                   SUNDAY, FEBRUARY 2, 2020                    |
      |                                                               |
      | Feb  2, 2020   6:00                                           |
      | > Hello world!                                                |
      | Feb  3, 2020  20:00                                           |
      | > Another entry from a different date!                        |
      +---------------------------------------------------------------+

   Here's what ``config.py`` looks like::

      from psp.stringify import PanelFormatter, EntryFormatter


      class MyPanelFormatter(PanelFormatter):
          def get_title(self, panel):
              # Make the panel title "Sunday, February 2, 2020" capitalized
              return super().get_title(panel).upper()


      class MyEntryFormatter(EntryFormatter):
          def get_basic_title(self, panel_date, entry_time):
              # Always display entry time fully, without hiding year or date
              return self.get_full_title(entry_time)


      # NOTE: This class has to be named PanelPrinter precisely!
      class PanelPrinter:
          def __init__(self, root_dir, width):
              #
              # Configure panel formatter so that:
              #
              #   *  entry time is displayed in 24-hour format
              #   *  1 vertical space between panel title and the first entry
              #   *  no space between each entry
              #
              self.formatter = MyPanelFormatter(width - 4,
                                                time_format='24 hour',
                                                title_entries_vsep=1,
                                                entry_vsep=0)
              # Configure entry formatter so that each line of an entry's
              # content is indented with '> '
              entry_formatter = MyEntryFormatter(content_indent='> ')
              self.formatter.set_entry_formatter(entry_formatter)

          def print(self, panel, file):
              cell_width = self.formatter.width
              bar = '+-' + ('-' * cell_width) + '-+'
              print(bar)
              for line in self.formatter.wrap(panel):
                  print(f'| {line:{cell_width}} |', file=file)
              print(bar)

Some more advanced uses:

*  An interactive prompt where you can experiment with stuff

   .. code-block:: console

      $ python -m psp interact backup.json
      Loading panels... done
      Launching an interacting prompt with the following variables:

          panels = [list of length 1]
          merged = [list of length 1]
          stdout = sys.stdout
          pp = pprint.pprint

      Python 3.9.6 (v3.9.6:db3ff76da1, Jun 28 2021, 11:49:53)
      [Clang 6.0 (clang-600.0.57)] on darwin
      Type "help", "copyright", "credits" or "license" for more information.
      (InteractiveConsole)
      >>> panels
      [<Panel object on 2020-02-02>]
      >>> pp(panels[0].get_entries())
      [<Entry object at 2020-02-02 06:00:00+08:00>,
       <Entry object at 2020-02-03 20:00:00+08:00>]

   Also you can do hacky code like this:

   .. code-block:: console

      >>> from psp.types import Entry
      >>> pp({name: getattr(panels[0].get_entry(0), name)
      ...     for name in Entry.__slots__})
      {'_date_time': datetime.datetime(2020, 2, 2, 6, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=28800))),
       '_encoding': 'utf-8',
       '_format': None,
       '_insight': False,
       '_panel': <Panel object on 2020-02-02>,
       '_raw': b'Hello world!',
       '_source': None,
       '_type': 'plain'}
