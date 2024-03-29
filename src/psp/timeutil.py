"""Time utility."""

__all__ = [
    'parse_timezone', 'parse_datetime', 'parse_date', 'parse_time',
    'is_naive',
    # 'get_local_timezone',
    'format_offset',
]

import re
# import time
import datetime

_RE_OFFSET = re.compile(r"""
    \A (?: UTC | GMT )?     # can be proceded with UTC or GMT
    (                       # group: time components
      [+-]                  #   sign
      \d{2} : \d{2}         #   hours and minutes
      (?:
        : \d{2}             #   seconds
        (?: \. \d{1,6} )?   #   microseconds
      )?
    )\Z
""", flags=re.VERBOSE)


# In a standalone context, the plus sign in a positive time zone only
# throws me off, so... here's my own implementation of parsing an offset.
# (Implementation detail, therefore private function)
def _parse_tz_offset(s):
    match = _RE_OFFSET.match(s)
    if not match:
        raise ValueError(f'invalid time offset: {s!r}')
    offset = match.group(1)
    try:
        return datetime.datetime.strptime(offset, '%z').tzinfo
    except ValueError:
        raise ValueError(f'invalid time offset: {s!r}') from None


def parse_timezone(s):
    """Parse a fixed time zone string.

    Return
    ------
    tz : datetime.tzinfo instance
        Return a `datetime.timezone` object with a fixed offset.

    Example
    -------
    >>> parse_timezone('UTC')
    datetime.timezone.utc
    >>> parse_timezone('08:00')
    datetime.timezone(datetime.timedelta(seconds=28800))
    """
    try:
        return _parse_tz_offset(s)
    except ValueError:
        pass
    if s in {'UTC', 'GMT'}:
        return datetime.timezone.utc
    raise ValueError(f'invalid time zone string: {s!r}')


def parse_datetime(s, tzinfo=None, fold=None):
    """Parse a date-time string."""
    try:
        parsed_dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(f'invalid datetime string: {s!r}') from None

    if tzinfo is not None and parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=tzinfo)
        if fold is not None:
            parsed_dt = parsed_dt.replace(fold=fold)
    return parsed_dt


def parse_date(s):
    """Parse a date string."""
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        raise ValueError(f'invalid date string: {s!r}') from None


def parse_time(s, tzinfo=None, fold=None):
    """Parse a time string."""
    try:
        parsed_time = datetime.time.fromisoformat(s)
    except ValueError:
        raise ValueError(f'invalid time string: {s!r}') from None
    if tzinfo is not None and parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=tzinfo)
        if fold is not None:
            parsed_time = parsed_time.replace(fold=fold)
    return parsed_time


def is_naive(dt):
    """Determine whether a datetime is naive as per the Python 3
    documentation.

    See: https://docs.python.org/3/library/datetime.html\
#determining-if-an-object-is-aware-or-naive
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


# def get_local_timezone():
#     """Return the local timezone as a datetime.timezone instance."""
#     localtime = time.localtime()
#     gmtoff = localtime.tm_gmtoff
#     zone = localtime.tm_zone
#     return datetime.timezone(datetime.timedelta(seconds=gmtoff), zone)


def format_offset(off):
    """Format a timedelta offset as returned by utcoffset().

    Copied from the Python implementation of the private function
    _format_offset() in the datetime module (used by functions like
    datetime.isoformat).
    """
    if off.days < 0:
        sign = '-'
        off = -off
    else:
        sign = '+'
    hh, mm = divmod(off, datetime.timedelta(hours=1))
    mm, ss = divmod(mm, datetime.timedelta(minutes=1))
    s = '%s%02d:%02d' % (sign, hh, mm)
    if ss or ss.microseconds:
        s += ':%02d' % ss.seconds
        if ss.microseconds:
            s += '.%06d' % ss.microseconds
    return s


def format_date(d):
    return d.isoformat()


def format_time(dt):
    return format_datetime(dt)[11:]


def format_datetime(dt):
    timespec = 'auto' if dt.second or dt.microsecond else 'minutes'
    return dt.isoformat(' ', timespec)
