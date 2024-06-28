# Development/contribution guides

more README for the curious :)

NOTE: if you are not very comfortable with command-line stuff, you are
always welcome to try out the (provisional) issue tracker on Codeberg!
More on that in `CONTRIB_CODEBERG.md`
([relative link](CONTRIB_CODEBERG.md))
([Codeberg link](https://codeberg.org/rapidcow/perspective/src/branch/main/CONTRIB_CODEBERG.md)).

## Setup

Assuming that you have activated a [virtual environment][venv], you can
clone this repo and install with [editable mode][] (this is so that any
changes you make here in the repo will be reflected in your Python runtime)

```sh
git clone https://git.rapidcow.org/perspective.git
# or if that doesn't work...
git clone https://codeberg.org/rapidcow/perspective.git
cd perspective/src
pip install -e .
```

Although weirdly enough if you import `psp` it tells you that it is a
namespace package... (because it can't find `__init__.py` somehow??

## How do I...

**Build documentation?** See `docs/README.md`
([relative link](docs/README.md))
([Codeberg link](https://codeberg.org/rapidcow/perspective/src/branch/main/docs)).

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

**Got questions?** Send [me](mailto:dev@rapidcow.org) an email (and
include the word "Perspective" somewhere so I know what you are
talking about). Please note that while I plan to keep track of our
conversations (by that I mean assigning each email I get with
a number), I will not make it public on a mailing list (if there will
ever be one) unless you explicitly allow me to.  And even if you do,
you can choose to remain anonymous and I will replace your email with
a random but consistent identifier (so we know who is talking - at least
within the same thread.)

The only thing I ask you for is this... try to use a consistent name
and email.  And if you can, skim through [Codeberg issues][] to see
if your question has been asked before.  (It's empty - I know,
But maybe one day through some miraculous means it won't....)

[Codeberg issues]: https://codeberg.org/rapidcow/perspective/issues


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

[from here it's output of git diff --stat grc/<branch>..<branch>]
```

and you are set! just send this output to <dev@rapidcow.org> :)

Alternatively you can also send me patches:

```sh
git format-patch grc/<branch>..<branch>
```

PS: If you don't have a MUA you feel comfortable to use with Git
I *highly* recommend checking out [aerc](https://aerc-mail.org/)!
It works with command-line stuff very smoothly.

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
