# `psp` --- A rework of the `basicproc.py` program

(Go to [perspective](https://github.com/rapidcow/perspective/) for
instructions on how to install/uninstall this library.)

Similar to how you use [`basicproc.py`][], the plan is that you can do the
same while running it as a module.

For starters, say you have a `backup.json` file, like this:

    $ cat backup.json
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

Then you can use the `psp print` subcommand to print out a panel of entries
(in this case, the panel of date "2020-02-02"):

    $ python3 -m psp print backup.json --date=2020-02-02
                                Sunday, February 2, 2020


    6:00 AM
      Hello world!

    Feb  3   8:00 PM
      Another entry from a different date!

The `psp synopsis` subcommand prints out a summary of the input file:

    $ python3 -m psp synopsis backup.json
    info 'backup.json':
      panels: 1
      entries: 2
    total:
      panels: 1
      entries: 2

(The "total" might seem weird, but you will find it handy when you provide
multiple backup files.)

As for the `psp print` part, the exact same result can be achieved using
Python:

```python
from psp.processors import load_json
from psp.stringify import print_panel

# Load the panel
panel = load_json('backup.json', date='2020-02-02')
# Print the panel...!
print_panel(panel)
```

This gives you a lot more flexibility over some simple user interface as
well as deeper customization through subclassing.  For example, if you
prefer 24-hour format, you can configure the `time_format` option of the
underlying `PanelFormatter` like so:

```python
print_panel(panel, time_format='24 hour')
```

Things are highly customizable too!  Say for example you want the formatted
panel to meet the following requirements:

*   do not center the panel title
*   exclude the weekday in the panel title and make it entirely UPPERCASE
*   always display the full date of each entry

then you can subclass `PanelFormatter` and `EntryFormatter` like this:

```python
from psp.stringify import PanelFormatter, EntryFormatter

class MyPanelFormatter(PanelFormatter):
    def get_title(self, panel):
        # panel.date is the date of the panel (intuitively) as a
        # datetime.date object.
        date = panel.date
        # You can format this date in whatever way you want.
        # Here I'm just going to use strftime format and then convert it
        # to uppercase.
        return date.strftime(f'%B {date.day}, %Y').upper()

    def wrap_title(self, title):
        # We're using _wrap_paragraph() so that the title is left-aligned!
        # Default implementation uses _center_paragraph() in comparison.
        return self._wrap_paragraph(title)


class MyEntryFormatter(EntryFormatter):
    def get_title(self, panel_date, entry_time):
        # The EntryFormatter class defines three types of titles:
        # get_short_title(), get_long_title(), and get_full_title().
        # To get the full date (with year, month, and day), we're going
        # to use get_full_title().
        return self.get_full_title(entry_time)
```

So now you can write

```python
# Create a formatter for both panel and entry
panel_formatter = MyPanelFormatter()
entry_formatter = MyEntryFormatter()

# Format the panel as a string and explicitly
# provide an entry formatter
formatted_str = panel_formatter.format(
    panel, entry_formatter=entry_formatter)

# Print it out!
print(formatted_str)
```

which should print out this as a result:

```
FEBRUARY 2, 2020


Feb  2, 2020   6:00 AM
  Hello world!

Feb  3, 2020   8:00 PM
  Another entry from a different date!
```

There are plenty of different classes you can mess around with---even the
entries and panels themselves!  (See [`psp.extensions.bigentry`][bigentry]
for example; I use it personally to write blog-style diaries where I can
include graphics.)

There's also a ton of new interesting functions in the library... so be
excited when I write about them in a documentation!


[`basicproc.py`]: https://gist.github.com/rapidcow/a0490a57965061ae06e5c43b2c97e46c
[bigentry]: https://github.com/rapidcow/perspective/blob/master/src/psp/extensions/bigentry.py
