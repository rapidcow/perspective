# perspective

A Python library providing backup utility for the iOS journaling app
[Perspective][]!

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
have successfully installed, you may run `python3 -m psp -v` or just import
`psp` into Python.

And to uninstall the library, you will have to do manually delete the files
from your site packages directory, which you can find by running

```python
import site
print(site.getsitepackages())       # ...if installed without --user
print(site.getusersitepackages())   # ...if installed with --user
```

---

Documentations will be available in `docs/` or something.  I don't know,
haven't figured out how to put them up here (and it's also essentially
incomplete now).
I will include a brief introduction there so... please be patient with
me if this makes no sense to you now.


[Perspective]: https://apps.apple.com/app/id1186753097

