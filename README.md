# perspective

A Python library providing backup utility for the iOS journaling app
[Perspective][] (and diaries in general)![^1]

Documentation in English is available [here][docs].


## Installation

NOTE: Make sure you have Python 3.8+ installed, and replace `python3`
in the following commands with the name of your interpretor.  (For example,
this might be `py` on Windows.)

You may install globally or [activate a virtual environment][venv] first.

To install, use ONE of the following methods:

*   (from Test PyPI) You can probably try this I'm not sure if
    this is still up on test.pypi.org

    ```sh
    python3 -m pip install -i https://test.pypi.org/simple/ perspe
    ```

*   (from this repository directly)

    ```sh
    git clone https://github.com/rapidcow/perspective.git
    python3 -m pip install perspective/src
    ```

If you have successfully installed, running `python3 -m psp -V` should
print the version number.

To uninstall, run `python3 -m pip uninstall perspe`.

For a clumsy demo (WILL BE REPLACED IN THE FUTURE), you can find one
[here][Demo] at the moment.


## Building documentation

See `docs/README.md`.


## Bug

I have no idea how this works, but well...

If you find a bug, open a new issue [here][issues], add a Bug label
(probably) and be sure to address:

*   a minimal example that can reproduce the problem
*   what you expected to happen (link to the [documentation][docs] or
    whatever could help us understand the issue)
*   what you actually got (the full traceback and error message)


## Development

Assuming that you have activated a [virtual environment][venv], you can
clone this repo and install with [editable mode][-e] (this is so that any
changes you make here in the repo will be reflected in your Python runtime)

```sh
git clone https://github.com/rapidcow/perspective.git
cd perspective/src
pip install -e .
```

Use `python3 -m unittest` in the repository directory to run tests in
`tests/` and `newtests/`.


[Perspective]: http://blinky.co/perspective_app/
<!--
  As long as the file is still named README.md, this link should
  work...
-->
[Demo]: https://github.com/rapidcow/perspective/tree/master/src
[docs]: https://perspe.readthedocs.io/en/latest/
[venv]: https://docs.python.org/3/library/venv.html
[-e]: https://pip-python3.readthedocs.io/en/latest/reference/pip_install.html#editable-installs

[issues]: https://github.com/rapidcow/perspective/issues

[^1]: This was not an attempt to replace the app!  My intent was originally
      to back up my diaries in the app, but since waiting for the devs to
      update seemed impossible I had to manually back them up on my own....
      If you have any problem concerning this project, feel free to contact
      me at <thegentlecow@gmail.com>!
