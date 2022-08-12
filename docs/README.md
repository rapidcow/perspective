# Documentation

This is the source of the documentation for the Perspective library,
including [`basicproc.py`][] (archived), this `psp` package, and the
structure of `backup.json`!

This documentation written in reStructuredText and compiled with [Sphinx][].
HTML theme used there is [Furo](https://github.com/pradyunsg/furo) since it
has dark mode that protects my eyes from going blind Ovo

The web version of this documentation can be found [here][perspe] (hosted by
[Read The Docs][]!)


## Build

### Prerequisites

Make sure to install the dependencies first using
`python3 -m pip install -r requirements.txt`!

It is HIGHLY recommended (though not required) that you create and activate
a virtual environment first.  See the [Python docs][venv] for how to create
one.  For Mac it might look like this (run this in the root directory of
this repository):

```sh
python3 -m venv .env
source .env/bin/activate
pip install -r docs/requirements.txt
```


### HTML

In `docs/`:

```sh
# With Make
make html
# On Windows
make.bat html
# Without GNU Make
sphinx-build -M html src build
```

If the build succeeds, the documentation should be at `build/index.html`.


### General form

WARNING: options tables look quite bad in PDF

Replace `{target}` in the following code with:

*   `html` to make HTML (same as the previous section)
*   `clean` to remove the `build/` directory (effectively the same as
    `rm -r build/` I believe)
*   `doctest` to run [doctest][]
*   `latex` or `latexpdf` to make PDF

```sh
# With Make
make {target}
# On Windows
make.bat {target}
# Without GNU Make
sphinx-build -M {target} src build
```

Note that doctest on basicproc.py won't be run unless it is installed.
It's completely optional but you can install it by cloning the gist
like so:

```sh
git clone https://gist.github.com/a0490a57965061ae06e5c43b2c97e46c.git basicproc
pip install basicproc
```

After the installation is done you may remove the `basicproc/` directory.


### Building with a different language

The following is borrowed from steps 3 to 6 of the
[sphinx-intl quick guide][quick].  I'll use Simplified Chinese (zh_CN)
for the following examples, but just keep in mind it's the same for other
languages.

To make documentation:

```sh
# With Make
make -e SPHINXOPTS="-D language=zh_CN" html
# On Windows...?
set SPHINXOPTS="-D language=zh_CN"
make.bat html
# Without make
sphinx-build -M html src build -D language=zh_CN
```

As before, you may replace `html` with any of the aforementioned target
(like `latexpdf`.)

For adding translation of some language (with code `zh_CN` again):

```sh
make gettext
cd src && sphinx-intl update -p ../build/gettext -l zh_CN
```

From there you can edit the `.po` files in `locale/zh_CN/LC_MESSAGES/`.
(Sometimes you have to remove the `#, fuzzy` in order for the translation
to go through, as described [here](https://stackoverflow.com/a/44440757))


## Publishing to Read The Docs

It's automatic I guess so just making a commit is all that is needed
<!-- XXX: prolly update this useless description in the future -->


## About translation

I also translated a very tiny amount of Chinese... so let me know
if you think a fully-fledged translation is gonna help.  (If you are
reading this chances are your answer is no anyways lol)

My hope is to do more than just a machine translation (if you ever used
one of those you'd know how horrible they are) or any type of direct
translation really (like [this](https://docs.manim.org.cn/) is pretty
good, but given the time I have now I'd like to focus on just English
before anything crazy happens :/


[sphinx]: https://www.sphinx-doc.org/en/master/
[perspe]: https://perspe.readthedocs.io/en/latest/
[read the docs]: https://readthedocs.org/

[`basicproc.py`]: https://gist.github.com/rapidcow/a0490a57965061ae06e5c43b2c97e46c
[venv]: https://docs.python.org/3/library/venv.html
[doctest]: https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html
[quick]: https://www.sphinx-doc.org/en/master/usage/advanced/intl.html#quick-guide
