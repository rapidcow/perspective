"""Time utility."""

# date and time parsing is actually just date + ' ' + time
__all__ = [
    'parse_timezone', 'parse_datetime', 'parse_date', 'parse_time',
    'is_naive', 'get_local_timezone', 'to_utc',
]

import re
import time
import datetime
try:
    import zoneinfo
except ImportError:
    zoneinfo = None

_RE_OFFSET = re.compile(r"""
    ^([+-])?                # group 1: optional sign
    (                       # group 2: time component
      \d{2} : \d{2}         #   hours and minutes
      (?:
        \d{2}               #   seconds
        (?: \. \d{1,6} )?   #   microseconds
      )?
    )$
""", flags=re.VERBOSE)

DATETIME_FORMATS = [
    # Formats used on Mac
    '%B %d, %Y at %H:%M',
    '%A, %B %d, %Y at %H:%M',
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
    raise ValueError(f'invalid time zone: {s!r}')


def parse_datetime(s, tzinfo=None, fold=None):
    """Parse a date-time string."""
    parsed_dt = None
    try:
        parsed_dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in DATETIME_FORMATS:
        try:
            parsed_dt = datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    if parsed_dt is None:
        raise ValueError(f'invalid date time: {s!r}')

    if tzinfo is not None and parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=tzinfo)
    if fold is not None:
        parsed_dt = parsed_dt.replace(fold=fold)
    return parsed_dt


def parse_date(s):
    """Parse a date string."""
    return datetime.date.fromisoformat(s)


def parse_time(s, tzinfo=None, fold=None):
    """Parse a time string."""
    parsed_time = datetime.time.fromisoformat(s)
    if tzinfo is not None and parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=tzinfo)
    if fold is not None:
        parsed_time = parsed_time.replace(fold=fold)
    return parsed_time


def is_naive(dt):
    """Determine whether a datetime.datetime is naive as per the
    Python 3 documentation.

    See: {}
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


# The link is too fricking long so I have to do this for the
# code aesthetics TnT
is_naive.__doc__ = is_naive.__doc__.format(
    'https://docs.python.org/3/library/datetime.html'
    '#determining-if-an-object-is-aware-or-naive'
)


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
    s = ''
    if off is not None:
        if off.days < 0:
            sign = '-'
            off = -off
        else:
            sign = '+'
        hh, mm = divmod(off, datetime.timedelta(hours=1))
        mm, ss = divmod(mm, datetime.timedelta(minutes=1))
        s += '%s%02d:%02d' % (sign, hh, mm)
        if ss or ss.microseconds:
            s += ':%02d' % ss.seconds

            if ss.microseconds:
                s += '.%06d' % ss.microseconds
    return s


def compare_datetime(dt1, dt2):
    utc_time1 = dt1.astimezone(datetime.timezone.utc)
    utc_time2 = dt2.astimezone(datetime.timezone.utc)
    return _cmp(utc_time1, utc_time2)


def _cmp(x, y):
    return 0 if x == y else 1 if x > y else -1


def to_utc(dt):
    """Convert datetime to UTC"""
    return dt.astimezone(datetime.timezone.utc)
