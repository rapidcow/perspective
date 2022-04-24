# perspective

A Python library providing backup utility for the iOS journaling app
[Perspective][]![^1]

Now the library is pretty much complete... except potentially with
millions of bugs.  I might change the library slightly during this period
but there shouldn't be super big changes now.


## Installation

To install the library, download this repository, `cd` to `src/` and run

```sh
python3 -m pip install .
# Or install for current user only...
python3 -m pip install --user .
```

where `python3` is the name of your Python 3 interpretor.  To confirm you
have successfully installed, you may run `python3 -m psp -V` or just import
`psp` into Python.

And to uninstall the library, run

    python3 -m pip uninstall psp

---

Documentations will be available in `docs/` or something.  I don't know,
haven't figured out how to put them up here (and it's also essentially
incomplete now).
I will include a brief introduction there so... please be patient with
me if this makes no sense to you now.

(For a brief demo, you can find it [here][Demo].)


[Perspective]: http://blinky.co/perspective_app/
<!--
  As long as the file is still named README.md, this link should
  work...
-->
[Demo]: https://github.com/rapidcow/perspective/tree/master/src

[^1]: This was not an attempt to replace the app!  My intent was originally
      to back up my diaries in the app, but since waiting for the devs to
      update seemed impossible I had to manually back them up on my own....
      If you have any problem concerning this project, feel free to contact
      me at <thegentlecow@gmail.com>!
