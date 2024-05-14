# Development/contribution guides

more README for the curious :)

## Setup

Assuming that you have activated a [virtual environment][venv], you can
clone this repo and install with [editable mode][] (this is so that any
changes you make here in the repo will be reflected in your Python runtime)

```sh
git clone https://git.rapidcow.org/perspective.git
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

## Pull requests

Little known fact there is this thing called [git-request-pull][]
that lets you do precisely this

Here's an example workflow: let's say you have `origin`
set up to push to your fork and `grc` pulled from my repo:

```sh
# (the -o flag renames the usual origin remote)
git clone --origin grc https://git.rapidcow.org/perspective.git
# this clones the default branch (main).
# if you want to work on some other branches, you need to do:
git checkout <branch>
# now we will create the "fork", essentially a copy of my
# repository except you can make changes to it.
# if you use GitHub, you will need to create a git repository
# there and obtain the URL first:
git remote add origin <fork URL>
# now you just make any changes you want! once you are done,
# push whatever branch you were working on to your forked repo:
# (the -u is optional, as this overrides the default
# behavior of pushing <branch> to the cloned remote)
git push origin -u <branch>
```

given that the last command is what you ran, the
pull request literally translates to:

```sh
git request-pull grc/<branch> <URL of your fork> <branch>
# if it tells you <branch> is ambiguous i find
# refs/heads/<branch> working... somehow :/
```

which should give you something like this:

```
The following changes since commit [SHA1 of grc/branch]:

  [One-line description of grc/branch] (Date)

are available in the Git repository at:

  <fork URL> <branch>

for you to fetch changes up to [SHA1 of branch in fork URL]:

  [One-line description of branch] (Date)

----------------------------------------------------------------
Your Name (7):
      This is
      A git-shortlog
      Thingy
      With a
      List of
      Descriptions
      of your commits

(from here it's output of git diff --stat grc/<branch>..<branch>)
```

and you are set! just email this output to me at <dev@rapidcow.org> :)

Alternatively you can also send me patches:

```sh
git format-patch grc/<branch>..<branch>
```

(A mailing list will be here when I receive anything on this address
an empty mailing list would be kind of boring...)

## Code guidelines

(This was moved from docs/intro/contrib.rst)

Good code is hard to write, and I get that.  It's hard to even say that
I know what I am doing either!  Despite this, I will still list out a few
things I would like us to follow:

*   Adhere to [PEP 8][] whenever possible.  This includes: proper naming
    style (``like_this`` for variables and ``LikeThis`` for classes),
    use a leading underscore ``_like_this`` for private methods), four-space
    indentation, adding spaces for readability (except in keyword arguments),
    using Python idioms, using comments to explain the code when the reader
    might not get the purpose of the code right away.
*   Above all else, be consistent!
*   Docstrings aren't a must but are most certainly welcomed :D
    I personally stick to Numpy docstring conventions (I don't have a
    link at the moment but it's out there IIRC), but you are free to use
    any format you want as long as you make it readable even to people
    who don't program much :)

[Perspective]: http://blinky.co/perspective_app/
[venv]: https://docs.python.org/3/library/venv.html
[editable mode]: https://pip-python3.readthedocs.io/en/latest/reference/pip_install.html#editable-installs
[git-request-pull]: https://git-scm.com/docs/git-request-pull
[PEP 8]: https://peps.python.org/pep-0008/
