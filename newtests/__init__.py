"""New psp tests"""
import contextlib
import functools
import datetime
import tempfile
import pathlib

__all__ = [
    'tempdir', 'make_tempdir', 'open_with_unicode',
    'make_time', 'make_date', 'make_tz',
]


# modified version of tempfile that returns
# a pathlib.Path object instead
@contextlib.contextmanager
def make_tempdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


# function decorator that passes the temporary directory
# as an extra positional argument
class tempdir:
    __slots__ = ('f',)

    def __init__(self, f):
        self.f = f

    # descriptor protocol for instance methods / class methods?
    # (i forgor how this works)
    def __get__(self, obj, objtype=None):
        if hasattr(self.f, '__get__'):
            meth = self.f.__get__(obj, objtype)
        else:
            meth = types.MethodType(self.f, obj)
        return _tempdir(meth)

    # support for decorating static methods
    def __call__(self, *args, **kwargs):
        return _tempdir(self.f)(*args, **kwargs)


def _tempdir(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        with make_tempdir() as tmp:
            return f(tmp, *args, **kwargs)
    return inner


def open_with_unicode(file, mode='r'):
    return open(file, mode, encoding='utf-8')


def make_time(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S%z')


def make_date(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d').date()


def make_tz(**kwargs):
    return datetime.timezone(datetime.timedelta(**kwargs))
