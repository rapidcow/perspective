# New tests

These are "new" because I actually plan what to test and not write
whatever comes to mind

They are unable to fully replace the original tests so I had to
make a separate folder, but `python3 -m unittest` seems to run them
all anyways... so that shouldn't be a big deal.


## Some more useful info

Thought it'd be worth mentioning the utility functions I wrote

`tempdir` is a function decorator so that every time you call it
a temporary directory is created.  That new directory is created
as a `pathlib.Path` object where you can exploit its quirky
`__truediv__` hack to join paths:

    @tempdir
    def my_function(root):
        subdir = root / 'foo'
        subdir.mkdir()
        print('i made a directory at', where)

If you need the function to accept more arguments just add them
after `root`; `root` will only be the first positional argument,
and consequently calling it anything else would work too.

Methods work too, and I intentionally made it so that `self`
would still be your first argument (thanks to Python's descriptor
protocol).  Write your methods like this:

    @tempdir
    def test_a_very_cool_feature(self, root, *args, **kwargs):
        pass

`make_tempdir` is just a context manager that uses
`tempfile.TemporaryDirectory` under the hood except I'm lazy
and made it always return a `pathlib.Path` object

`open_with_unicode` is literally `functools.partial(open, encoding='utf-8')`
except I didn't write it in that way... because I'm **stupid** Q.Q

`make_time`, `make_date`, `make_tz`... use them like this:

    make_time('2021-12-17 14:00:00+0800')
    make_date('2021-12-17')
    make_tz(hours=8)

(Precisely this format!  You can probably add in the colons for `%z`
but I'm pretty sure it doesn't work for versions older than Python 3.7)
