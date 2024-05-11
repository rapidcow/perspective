# perspective - diary backup helper

Heyoooooooo I'm hosting this project on my own cgit server!
(That means no more GitHub bots, teehee >:)

Info about this project will also be available on
<http://rapidcow.org/projects/perspective> one day!

The current README.md is preserved for the time being
(well, mostly - there are big modifications as I am
very excited ;)
If you a curious to see how you can help me code,
I've moved that part of the readme to
[CONTRIB.md](/perspective/about/CONTRIB.md).

---

A Python library providing backup utility inspired by the
iOS journaling app [Perspective][] (and diaries in general)!

To clear things up, I often refer to the library as simply the
Perspective library, though please understand that I am by no
means claiming it as a trademark or anything crazy like that.
I'm just someone who prefers not to have my diaries perish when
I stop using my iPhone one day - and well, I've written so
much code, and I have to call it something.

The code, of course, is written from scratch by me independently
of the developers of Perspective (Blinky, IIRC?)
(I hope I'm not doing anything wrong here, but you must let
me know something, well, email me at <yizzy@rapidcow.org> or
<ethan@rapidcow.org> idk...)

The Perspective library is released under GPLv3.
Do whatever crazy stuff you want with it; as long as you
don't use it for something locked behind a paywall and
I will be happy. :)

## Installation

The Perspective library is written for Python 3.8 and above.
(Python 3.9 + the tzdata package is recommended for IANA
timezone recognition.)

You may install globally or [activate a virtual environment][venv] first.

To install, do this:

    python3 -m pip install git+https://rapidcow.org/perspective.git@v0.1#subdirectory=src

If you have successfully installed, running `python3 -m psp -V`
should print the version number.

To uninstall, run `python3 -m pip uninstall perspe`.

## What can it do?

In a nutshell, the Perspective library reads your diary entries
from JSON files like these:

```json
{ "tz": "+08:00", "path": ["photos"], "data": [
  { "date": "2024-05-01", "rating": ":)", "entries": [
    { "time": "12:34", "data": "hey guys i drew a cow" },
    { "time": "12:35", "input": "COW.jpg" },
    { "time": "14:44", "data": "stop rushing me everything mom!!! >:((" },
    { "time": "19:00", "data": "where did everything go...." },
    { "date-time": "2024-05-02 02:17",
      "data": "i will never forget you..." },
    { "date-time": "2024-05-06 23:18", "insight": true,
      "data": "lol that's a very cowish cow" }
  ]},
  { "date": "2024-05-06", "rating": ":|", "entries": [
    { "time": "15:17+00:00", "data": "i made git.rapidcow.org work!" },
    { "date-time": "12:54-04:00", "data": "i'm back :)" },
    { "date-time": "2024-05-07 01:28",
      "data": "wait that was the wrong time zone sorry" }
  ]}
]}
```

into these:

```pycon
>>> from psp.serializers import JSONLoader
>>> # with base_dir the photos/ path becomes /path/to/my/photos/
>>> with open('/path/to/my/backup.json', encoding='utf-8') as fp:
...     panels = list(JSONLoader(base_dir='/path/to/my').load(fp))
>>> panels
[<Panel object on 2024-05-01>, <Panel object on 2024-05-06>]
>>> panels[0].get_entries()
[<Entry object at 2024-05-01 12:34:00+08:00>,
 <Entry object at 2024-05-01 12:35:00+08:00>,
 <Entry object at 2024-05-01 14:44:00+08:00>,
 <Entry object at 2024-05-01 19:00:00+08:00>,
 <Entry object at 2024-05-02 02:17:00+08:00>,
 <Entry object at 2024-05-06 23:18:00+08:00>]
```

which you can then print like this:

```pycon
>>> from psp.stringify import PanelFormatter
>>> formatted = PanelFormatter(width=48).format(panels[0])
>>> print('=' * 48); print(formatted); print('=' * 48)
==========================================
          Wednesday, May 1, 2024


12:34 PM
  hey guys i drew a cow

12:35 PM
  <binary file sized 81.8 kB at '/path/to/
   my/photos/COW.jpg'>

2:44 PM
  stop rushing me everything mom!!! >:((

7:00 PM
  where did everything go....

May  2   2:17 AM
  i will never forget you...


Insight
-------
May  6  11:18 PM
  lol that's a very cowish cow
==========================================
```

Actually I can talk a little bit more about this: you see
time zones are an integral part of this whole library,
and the stringify package is perhaps the best example of this.
You can, for example, tell it to convert everything into
the same time zone for you:

```pycon
>>> # the indent argument allows any arbitrary prefix:
>>> formatter = PanelFormatter(width=46, indent='# ')
>>> # set time zone to +08:00 from the 3rd entry
>>> formatter.configure(time_zone=panels[1].get_entry(2).time.tzinfo)
>>> # now we can set this option:
>>> formatter.configure(coerce_time_zone=True)
>>> # and everything will be displayed in +08:00...
>>> formatted = formatter.format(panels[1])
>>> print('#' + '=' * 47); print(formatted); print('#' + '=' * 47)
#===============================================
#           Monday, May 6, 2024  :|
#
#
# 11:17 PM
#   i made git.rapidcow.org work!
#
# May  7  12:54 AM
#   i'm back :)
#
# May  7   1:00 AM
#   wait that was the wrong time zone sorry
#===============================================
```

Or maybe you want to just display the time zones as is:

```pycon
>>> formatter.configure(coerce_time_zone=False)
>>> formatted = formatter.format(panels[1])
>>> print('#' + '=' * 47); print(formatted); print('#' + '=' * 47)
#===============================================
#           Monday, May 6, 2024  :|
#
#
# 3:17 PM [+00:00]
#   i made git.rapidcow.org work!
#
# 12:54 PM [-04:00]
#   i'm back :)
#
# May  7   1:00 AM
#   wait that was the wrong time zone sorry
#===============================================
```

Notice how the third entry has a consistent offset with
the time zone we passed, and so the formatter hides it.
By default, time zones are either entirely hidden only if they
have the same offset (as in our first case) or entirely shown:

```pycon
>>> # unset the time zone - this is the default
>>> formatter.configure(time_zone=None)
>>> formatted = formatter.format(panels[1])
>>> print('#' + '=' * 47); print(formatted); print('#' + '=' * 47)
#===============================================
#           Monday, May 6, 2024  :|
#
#
# 3:17 PM [+00:00]
#   i made git.rapidcow.org work!
#
# 12:54 PM [-04:00]
#   i'm back :)
#
# May  7   1:00 AM [+08:00]
#   wait that was the wrong time zone sorry
#===============================================
```

And that's only a glimpse of what the library can do!
Here's some more to name:

*  built-in sanity check (good to have when you type the
   JSON by hand and want to know it makes sense)
*  programming-friendly API (entry, panel, parsers)
*  file type/extension inference and management
   (mostly to save typing where the distinction between
   text entries and binary entries is blurry)
*  a loader that understands external paths if your data
   takes up too much space in the JSON (at the moment the
   loader is quite strict about the file's existence, though
   the plan is to make it work with broken links so you can
   use say git-annex with it!)
*  a dumper where you have full control over file paths
   you want to export the files to (for those who really
   hate hash gibberish the same way like I do)
*  a formatter - wait, I mentioned this didn't I... oh yeah.
   teehee sorry =v=

And even MORE I have in mind but haven't implemented
(no promises! though I'd be excited if this becomes that)

*  a command-line interface with a git-commit-like work flow
   that lets you write diaries into JSON more easily
   (heck, who said it had to be JSON? anything you can turn
   into a Python `dict` and vise versa are equally valid
   for storing these guys! though that means I will
   have to allow arbitrary filters... somehow. i don't know how tbh.)
*  a simple webapp that makes it possible to actually view images
   (and not have it printed as simply "binary file sizes XXX" -
   well i have this personally. but the way i did was so hacky
   i'm not including it here...)
*  internal links to other entries
*  support for add-on fields like image alt text and
   audio transcriptions (in a less hacky way hopefully...)
   (speaking of which **attachments** is my current idea for
   replacing bigentries!)
*  full text search, fuzzy search, and the like (though with the
   API now you can easily write a script that matches the
   contents of your entries with regex ;)
*  search & query in general to make communication with other
   programs easier (it's, again, not impossible, but at the
   moment doing it means that... you'd have to be on your own :/)

If you want to learn more, check out my largely unfinished
[documentation][docs]. I gave a few examples there too, which
might be of more interest to you.

## Bugs

Email <dev@rapidcow.org>! I might figure out how to create
a mailing list one day, but here are some basic expectations
if you report stuff you find:

*   a minimal example that can reproduce the problem
*   what you expected to happen (link to the [documentation][docs] or
    whatever could help me understand the issue)
*   what you actually got (the **full** traceback and error message)

Suggestions are equally welcome, although please be practical
since there's just the one of me

[Perspective]: http://blinky.co/perspective_app/
[docs]: https://perspe.readthedocs.io/en/latest/
[venv]: https://docs.python.org/3/library/venv.html
