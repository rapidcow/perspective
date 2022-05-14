"""Time utility."""

__all__ = [
    'parse_timezone', 'parse_datetime', 'parse_date', 'parse_time',
    'is_naive', 'get_local_timezone', 'format_offset',
]

import re
import time
import datetime
# 'zoneinfo' is a module introduced in Python 3.9.  The first-party package
# 'tzdata' may be installed with pip so that 'parse_timezone()' handles
# named regions such as "America/Los_Angeles".
#
# Since we only require the users to have a Python 3.8 distribution, this is
# an optional feature of this module.
try:
    import zoneinfo
except ImportError:
    zoneinfo = None

_RE_OFFSET = re.compile(r"""
    \A (?: UTC | GMT )?     # can be proceded with UTC or GMT
    ([+-])?                 # group 1: optional sign
    (                       # group 2: time component
      \d{2} : \d{2}         #   hours and minutes
      (?:
        \d{2}               #   seconds
        (?: \. \d{1,6} )?   #   microseconds
      )?
    )\Z
""", flags=re.VERBOSE)

# Public interface for adding more formats timeutil (used by JSONLoader)
# can recognize...?
DATETIME_FORMATS = [
    # Formats used on Mac
    '%B %d, %Y at %H:%M',
    '%A, %B %d, %Y at %H:%M',
    # ctime format (these two are equivalent)
    '%c', '%a %b %d %H:%M:%S %Y',
    '%a %b %d %H:%M:%S%z %Y', '%a %b %d %H:%M %Y',
    # ctime format without the weekday
    '%b %d %H:%M:%S %Y', '%b %d %H:%M %Y', '%b %d %H:%M:%S%z %Y',
    # Miscellaneous
    '%m/%d/%y %H:%M:%S%z',
    '%m/%d/%y %H:%M:%S',
    '%m/%d/%y %H:%M',
]

TIME_FORMATS = [
    # 12-hour format
    '%I:%M %p', '%I:%M%z %p',
    '%I:%M:%S %p', '%I:%M:%S%z %p',
    '%I:%M:%S.%f %p', '%I:%M:%S.%f%z %p',
]

DATE_FORMATS = [
    '%b %d %Y', '%b %d, %Y', '%B %d %Y', '%B %d, %Y',
    '%a %b %d %Y', '%a, %b %d, %Y', '%A %B %d %Y', '%A, %B %d, %Y',
    '%d %b %Y', '%d %b, %Y', '%d %B %Y', '%d %B, %Y',
    '%a %d %b %Y', '%a, %d %b, %Y', '%A %d %B %Y', '%A, %d %B, %Y',
    '%m/%d/%y', '%m/%d/%Y',
]


# In a standalone context, the plus sign in a positive time zone only
# throws me off, so... here's my own implementation of parsing an offset.
# (Implementation detail, therefore private function)
def _parse_tz_offset(s):
    match = _RE_OFFSET.match(s)
    if not match:
        raise ValueError(f'invalid time offset: {s!r}')
    sign, offset_str = match.groups()
    # sign is one of '+', '-', or None.  Only '-' negates the sign.
    if sign is None:
        sign = '+'
    try:
        return datetime.datetime.strptime(sign + offset_str, '%z').tzinfo
    except ValueError:
        raise ValueError(f'invalid time offset: {s!r}') from None


def parse_timezone(s):
    """Parse a time zone string.

    Return
    ------
    tz : datetime.tzinfo instance
        Return a `datetime.timezone` object for a fixed offset,
        or a `zoneinfo.ZoneInfo` object for a valid IANA name.

    Example
    -------
    >>> parse_timezone('UTC')
    datetime.timezone.utc
    >>> parse_timezone('08:00')
    datetime.timezone(datetime.timedelta(seconds=28800))

    The following example only runs for Python 3.9+ and if `tzdata`
    (https://pypi.org/project/tzdata/) is installed:

    >>> parse_timezone('America/Los_Angeles')
    zoneinfo.ZoneInfo(key='America/Los_Angeles')
    """
    try:
        return _parse_tz_offset(s)
    except ValueError:
        pass
    if s in ('UTC', 'GMT'):
        return datetime.timezone.utc
    if zoneinfo is not None:
        try:
            return zoneinfo.ZoneInfo(s)
        except zoneinfo.ZoneInfoNotFoundError:
            pass
    raise ValueError(f'invalid time zone string: {s!r}')


def parse_datetime(s, tzinfo=None, fold=None):
    """Parse a date-time string."""
    try:
        parsed_dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        for fmt in DATETIME_FORMATS:
            try:
                parsed_dt = datetime.datetime.strptime(s, fmt)
            except ValueError:
                continue
            break
        else:
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
        for fmt in DATE_FORMATS:
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        else:
            raise ValueError(f'invalid date string: {s!r}') from None


def parse_time(s, tzinfo=None, fold=None):
    """Parse a time string."""
    try:
        parsed_time = datetime.time.fromisoformat(s)
    except ValueError:
        for fmt in TIME_FORMATS:
            try:
                parsed_time = datetime.datetime.strptime(s, fmt).timetz()
            except ValueError:
                continue
            break
        else:
            raise ValueError(f'invalid time string: {s!r}') from None
    if tzinfo is not None and parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=tzinfo)
    if fold is not None:
        parsed_time = parsed_time.replace(fold=fold)
    return parsed_time


def is_naive(dt):
    """Determine whether a datetime.datetime is naive as per the
    Python 3 documentation.

    See: https://docs.python.org/3/library/datetime.html\
#determining-if-an-object-is-aware-or-naive
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


def get_local_timezone():
    """Return the local timezone as a datetime.timezone instance."""
    localtime = time.localtime()
    gmtoff = localtime.tm_gmtoff
    zone = localtime.tm_zone
    return datetime.timezone(datetime.timedelta(seconds=gmtoff), zone)


def format_offset(off):
    """Format an offset as returned by utcoffset().

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
