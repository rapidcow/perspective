# `psp` --- A rework of the `basicproc.py` program

Similar to how you use `basicproc.py`, the plan is that you can do the
same while running it as a module (make sure to install it first using
`python3 -m pip install .`!):

Comes with convenient command-line tools (which I hope you find somewhat
useful...)

    $ cat backup.json
    {
      "tz": "+08:00",
      "data": [
        {
          "date": "2020-02-02",
          "entries": [
            {
              "time": "06:00",
              "data": "Hello!"
            },
            {
              "date-time": "2020-02-03 20:00",
              "data": "Another entry from a different date!"
            }
          ]
        }
      ]
    }
    $ python3 -m psp print backup.json --date=2020-02-02
                                Sunday, February 2, 2020


    6:00 AM
      Hello!

    Feb  3   8:00 PM
      Another entry from a different date!

The same can be achieved using Python!

```python
from psp.processors import load_json
from psp.stringify import print_panel
# Load the panel
panel = load_json('backup.json', date='2020-02-02')
# Print the panel...!
print_panel(panel)

# If you prefer 24-hour format, configure the 'time_format' option
# of the underlying PanelFormatter like this!
print_panel(panel, time_format='24 hour')
```

Things are highly customizable too!  Say for example if you don't want to
center the panel title, exclude the weekday, and you always want to see
the full date of each panel, then you can subclass `PanelFormatter` and
`EntryFormatter` like this:

```python
from psp.stringify import PanelFormatter, EntryFormatter

class MyPanelFormatter(PanelFormatter):
    def wrap_title(self, title):
        # We're using _wrap_paragraph() so that the title is left-aligned!
        # Default implementation uses _center_paragraph() in comparison.
        return self._wrap_paragraph(title)

    def get_title(self, panel):
        # panel.date is the date of the panel (intuitively) as a
        # datetime.date object.
        date = panel.date
        # You can format this date in whatever way you want.
        # Here I'm just going to use strftime format.
        return date.strftime(f'%B {date.day}, %Y')


class MyEntryFormatter(EntryFormatter):
    def get_title(self, panel_date, entry_time):
        # The EntryFormatter class defines three types of titles:
        # get_short_title(), get_long_title(), and get_full_title().
        # To get the full date (with year, month, and day), we're going
        # to use get_full_title().
        return self.get_full_title(entry_time)
```

So now you can do

```python
# Create a new formatter
panel_formatter = MyPanelFormatter()
entry_formatter = MyEntryFormatter()

# Format the panel as a string
formatted_str = panel_formatter.format(
    panel, entry_formatter=entry_formatter)

# Print it out!
print(formatted_str)
```

which gives you this:

```
February 2, 2020


Feb  2, 2020   6:00 AM
  Hello!

Feb  3, 2020   8:00 PM
  Another entry from a different date!
```

There are plenty of different classes you can mess around with---even the
entries and panels themselves!  (See `psp.extensions.bigentry` for example;
I use it personally to write blog-style diaries where I can include
graphics.)

---

On an additional note, to uninstall this, go to your local `site-packages/`
folder, which you can find by running the following in Python:

```python
import site
print(site.getsitepackages())
```

and find files with `psp` prefix and delete them.  Simple!

There's also a ton of new interesting functions in the library... so be
excited when I write about them in a documentation!
