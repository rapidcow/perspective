"""Core classes of for Perspective data types."""

__all__ = ['Panel', 'Entry']

import datetime
import os
from . import timeutil


def _assert_type(obj, objtype, name):
    # Used for asserting type for __init__
    if not isinstance(obj, objtype):
        # We shouldn't need __qualname__ if subclass(objtype, type)...
        # Display the module name only if the class is imported
        clsname = (objtype.__name__
                   if objtype.__module__ in {'builtins', __name__}
                   else f'{objtype.__module__}.{objtype.__name__}')
        article = 'an' if clsname in {'Entry'} else 'a'
        raise TypeError(f'{name} should be {article} {clsname} object, '
                        f'not {obj!r}')


class Panel:
    """Panel containing entries for a single day."""
    __slots__ = (
        'date', 'entries', 'attrs',
    )

    def __init__(self, date):
        self.date = date
        self.entries = []
        self.attrs = {'rating': None}

    def __repr__(self):
        clsname = type(self).__name__
        # use the builtin str() representation of datetime.date
        return '<{} object on {}>'.format(clsname, self.date)

    def validate(self):
        # raises ValueError (generic) / TypeError (confusing types)
        pass

    # # A method that works like the replace() methods in datetime
    # def replace(self, *, date=None, entries=None, attrs=None):
    #     if date is None:
    #         date = self.date
    #     if entries is None:
    #         entries = self.entries
    #     if attrs is None:
    #         attrs = self.attrs
    #     obj = type(self)(date)
    #     obj.entries = entries
    #     obj.attrs = attrs
    #     return obj


# date_time MUST be an aware datetime object
class Entry:
    """Entry containing text or binary data."""
    __slots__ = (
        'panel', 'date_time', 'insight',
        'data', 'meta', 'attrs',
    )

    def __init__(self, panel, date_time):
        _assert_type(panel, Panel, 'panel')
        self.panel = panel
        _assert_type(date_time, datetime.datetime, 'date_time')
        if timeutil.is_naive(date_time):
            raise TypeError('date_time should be an aware datetime object')
        self.date_time = date_time
        self.insight = False
        self.data = {
            'type': None,
            'format': None,
            'encoding': None,
        }
        self.meta = {}
        self.attrs = {
            'question': None,
        }

    def __repr__(self):
        clsname = type(self).__name__
        # use the builtin str() representation of datetime.datetime
        return '<{} object at {}>'.format(clsname, self.date_time)

    def validate(self):
        # raises ValueError (generic) / TypeError (confusing types)

        # Time check
        # ----------
        time = self.date_time
        # Only determine the start of day by the local time zone!
        local_offset = time.utcoffset()
        panel_date = self.panel.date
        midnight = datetime.time()
        start_of_day = (datetime.datetime.combine(panel_date, midnight)
                        - local_offset)
        time_utc = (self.date_time.astimezone(datetime.timezone.utc)
                    .replace(tzinfo=None))

        if time_utc < start_of_day:
            raise ValueError('entry time ({}) earlier than start of day of '
                             'the parent panel ({}) in local time'
                             .format(time, panel_date))

        start_of_insight = start_of_day + datetime.timedelta(days=2)
        if self.insight and time_utc < start_of_insight:
            raise ValueError('entry is an insight and its time ({}) is '
                             'less than 2 days apart from the start of day '
                             'of the parent panel ({}) in local time'
                             .format(time, panel_date))

        # Metadata
        # --------
        self.meta.setdefault('posted', None)
        self.meta.setdefault('created', None)

        # Posting time should be equal or greater than the entry time.
        # No tolerance is needed as the time without seconds itself is
        # already the lower bound.
        #
        # We accept None for the 'posted' attribute (otherwise the
        # initialization would be way too complicated), although it would
        # always be set when loaded by json_processor.JSONLoader.
        posted = self.meta['posted'] or time
        if posted < time:
            raise ValueError('time posted before entry time')

        # Creation time should be less than or equal to the entry time.
        # When the entry time has 0 seconds and 0 microseconds,
        # creation time should be before the start of the next minute.
        created = self.meta['created']

        # In case the second value isn't provided (most cases),
        # allow up to 1 minute of difference
        if time.second == 0 and time.microsecond == 0:
            tolerance = datetime.timedelta(seconds=60)
        else:
            tolerance = datetime.timedelta(0)
        if created is not None and created > posted + tolerance:
            raise ValueError('creation time after posted time')

        self.__validate_source_path()

    def __validate_source_path(self):
        try:
            source = self.data['source']
        except KeyError:
            return
        if not isinstance(source, (str, os.PathLike)):
            raise TypeError(f'source path should be str or os.PathLike, '
                            f'not {source!r}')
        try:
            with open(source, 'rb') as fp:
                pass
        except OSError as exc:
            if not os.path.exists(source):
                raise ValueError(f'source path {source!r} does not exist')
            if not os.path.isfile(source):
                raise ValueError(f'source path {source!r} is not a file')
            # We don't know what caused it... err.....
            raise ValueError(f'invalid source path {source!r}') from exc

    # In basicproc.py, this is the is_binary() method.
    # The exact definition of being "binary" isn't so clear, so I decided
    # to negate the term and call it is_text() instead.  It still works
    # exactly the same as `not self.is_binary()` would've.
    def is_text(self):
        enc = self.data['encoding']
        if enc is None:
            raise ValueError('encoding is not set')
        return enc != 'binary'

    # slightly modified from basicproc
    def load_data(self):
        if 'raw' in self.data:
            return self.data['raw']
        content = self.get_raw_data()
        self.data['raw'] = content
        return content

    def get_raw_data(self):
        if 'raw' in self.data:
            return self.data['raw']
        with open(self.data['source'], 'rb') as fp:
            return fp.read()

    # Get data -> str or bytes
    # (Convenience method)
    def get_data(self):
        if self.is_text():
            return self.get_raw_data().decode(self.data['encoding'])
        else:
            return self.get_raw_data()

    # # Don't use this bad method >:/
    # def __unload_data(self, to_file=None):
    #     if to_file is not None:
    #         src = to_file
    #     else:
    #         src = self.data['source']
    #     raw = self.data['raw']
    #
    #     if os.path.exists(src):
    #         if os.path.isfile(src):
    #             with open(src, 'rb') as fp:
    #                 file_raw = fp.read()
    #             if file_raw != raw:
    #                 raise ValueError(f"file {src!r} exists and its "
    #                                  f"content does not match "
    #                                  f"self.data['raw']")
    #         else:
    #             import errno
    #             raise FileExistsError(errno.EEXIST, strerror(errno.EEXIST),
    #                                   src)
    #     else:
    #         with open(src, 'wb+') as fp:
    #             fp.write(self.data['raw'])
    #
    #     self.data['source'] = src
    #     del self.data['raw']

    # def replace(self, *, panel=None, date_time=None, insight=None,
    #             data=None, meta=None, attrs=None):
    #     if panel is None:
    #         panel = self.panel
    #     if date_time is None:
    #         date_time = self.date_time
    #     if insight is None:
    #         insight = self.insight
    #     if data is None:
    #         data = self.data
    #     if meta is None:
    #         meta = self.meta
    #     if attrs is None:
    #         attrs = self.attrs
    #     obj = type(self)(panel, date_time)
    #     obj.insight = insight
    #     obj.data = data
    #     obj.meta = meta
    #     obj.attrs = attrs
    #     return obj


# Experimental: a BIG entry.
# This is basically like an article, but instead of just having a file as
# in the case for Entry, we also have a zip archive (to make life simplier)
# that holds images/videos that is to be unzipped in the same directory
# the main file is in.

# class BigEntry:
#     pass
