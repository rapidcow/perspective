# `psp` --- A rework of the `basicproc.py` program

Similar to how you use `basicproc.py`, the plan is that you can do the
same while running it as a module (make sure to install it first using
`python setup.py install`!):

    $ cat backup.json
    {
      "tz": "+08:00",
      "data": [
        {
          "date": "2020-02-02",
          "entries": [
            {
              "time": "06:00",
              "data": "Hello!"
            }
          ]
        }
      ]
    }
    $ python -m psp print backup.json --date=2020-02-02
                             Sunday, February 2, 2020


    6:00 AM
      Hello!

To uninstall it, go to your local `site-package` folder, which you can find
by running the following in Python:

    import site
    print(site.getsitepackages())

and find files with `psp` prefix and delete them.  Simple!

There's also a ton of new interesting functions in the library... so be
excited when I write about them in a documentation!
