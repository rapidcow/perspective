# Documentation

...except this IS my first rodeo. >-0

This will be a documentation about [`basicproc.py`][] (archived),
this `psp` library, and the structure of `backup.json`!

In addition to that the documentation will be available in
(simplified) Chinese!
毕竟我自己就会说中文 ;D (当然说得好不好是另一回事 XD)


## Setup

Get a [virtual environment][] first if you haven't got one already
(this is in your shell/terminal/command prompt/whatever):

    python -m venv .env

Then activate it with something like:

    source .env/bin/activate

That is what I would run on Mac with a Bash shell.
[Yours might be different...][virtual environment]

Next install Sphinx:

    pip install Sphinx

And you should be good to go! (btw sphinx-quickstart is what i used to
create this documentation, but since it's already created you don't
have to worry about that)


## Build

Inside the `docs` directory, run

    make html

To make documentation in other languages (say `zh_CN` for Simplified
Chinese), run

    make -e SPHINXOPTS="-D language=zh_CN" html

You might find step 6 of this [quick guide][] helpful.
There it would also show you how to generate the `.po` files.


## Other cool stuff

`make latex` for creating PDF documents! (`make latexpdf` does the
compilation automatically)

`make doctest` to run tests (not sure if it will run properly but I'm
sure you need [`basicproc.py`][] installed somehow... I'll figure out
whether I want to include `basicproc.py` one day, okay...?)

[`basicproc.py`]: https://gist.github.com/rapidcow/a0490a57965061ae06e5c43b2c97e46c
[virtual environment]: https://docs.python.org/3/library/venv.html
[quick guide]: https://www.sphinx-doc.org/en/master/usage/advanced/intl.html#quick-guide
