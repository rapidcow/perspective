# perspective

**NOTICE**: I'M NOT DOOOOONE please don't count too much on the interface
i might change :(

A Python library providing backup utility for the iOS journaling app
[Perspective][] (and diaries in general)!

Documentation in English is available [here][docs].


## Installation

NOTE: Make sure you have Python 3.8+ installed, and replace `python3`
in the following commands with the name of your interpretor.  (For example,
this might be `py` on Windows.)

You may install globally or [activate a virtual environment][venv] first.

To install, use ONE of the following methods:

*   from this repository directly, RECOMMENDED

    ```sh
    git clone https://github.com/rapidcow/perspective.git
    python3 -m pip install perspective/src
    ```

*   from Test PyPI, NOT RECOMMENDED as it is *very* out of date

    ```sh
    python3 -m pip install -i https://test.pypi.org/simple/ perspe==0.2.0a1
    ```

If you have successfully installed, running `python3 -m psp -V` should
print the version number.

To uninstall, run `python3 -m pip uninstall perspe`.


## Building documentation

See `docs/README.md`.


## Bug

I have no idea how this works, but well...

If you find a bug, open a new issue [here][issues], add a Bug label
(probably) and be sure to address:

*   a minimal example that can reproduce the problem
*   what you expected to happen (link to the [documentation][docs] or
    whatever could help me (@rapidcow) understand the issue)
*   what you actually got (the **full** traceback and error message)


## Development

Assuming that you have activated a [virtual environment][venv], you can
clone this repo and install with [editable mode][] (this is so that any
changes you make here in the repo will be reflected in your Python runtime)

```sh
git clone https://github.com/rapidcow/perspective.git
cd perspective/src
pip install -e .
```

Although weirdly enough if you import `psp` it tells you that it is a
namespace package... (because it can't find `__init__.py` somehow??


## Unit tests

In this directory, run:

```python
# old tests
python3 -m unittest discover -s tests -t .
# new tests
python3 -m unittest discover -s newtests -t .
```

Due to the use of packages calling without the `-t` option
would give import errors...


## Publishing on <s>PyPI</s> Test PyPI

From [this](https://packaging.python.org/en/latest/tutorials/packaging-projects/):

```sh
python3 -m pip install --upgrade build twine
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

(you will need your password for the last command)

[Perspective]: http://blinky.co/perspective_app/
[docs]: https://perspe.readthedocs.io/en/latest/
[venv]: https://docs.python.org/3/library/venv.html
[editable mode]: https://pip-python3.readthedocs.io/en/latest/reference/pip_install.html#editable-installs

[issues]: https://github.com/rapidcow/perspective/issues
