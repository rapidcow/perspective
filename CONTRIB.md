# Contribution

## Setup

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

## How do I...

**Build documentation?** See `docs/README.md`.

**Run tests?** At the root of this worktree:

```python
# old tests
python3 -m unittest discover -s tests -t .
# new tests
python3 -m unittest discover -s newtests -t .
```

Due to the use of packages in my unit test code calling without
the `-t` option would cause import errors...


**Publish to <s>PyPI</s> Test PyPI?**
from [this](https://packaging.python.org/en/latest/tutorials/packaging-projects/):

```sh
python3 -m pip install --upgrade build twine
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

(you will need your password for the last command)


## Pull requests?

I don't think we will do that here :) just submit patches
with `git-format-patch(1)` to &lt;<dev@rapidcow.org>&gt;
so I can review and apply them. Be sure to use set your
name and email properly so everyone knows it's your work!
(and know who to "blame" when things go wrong, ahem...)

[Perspective]: http://blinky.co/perspective_app/
[venv]: https://docs.python.org/3/library/venv.html
[editable mode]: https://pip-python3.readthedocs.io/en/latest/reference/pip_install.html#editable-installs
