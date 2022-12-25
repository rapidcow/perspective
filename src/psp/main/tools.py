"""Useful tools for psp projects."""

import calendar
import datetime
import functools
import importlib.util
import itertools
import os
import shutil
import subprocess as sp
import sys
import textwrap

__all__ = [
    'termcolor', 'DateRequester',
    'check_panel_attributes', 'load_module_from_file',
]

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]

MONTH_ABBRS = [m[:3] for m in MONTH_NAMES]


# Code adapted from: https://gist.github.com/martin-ueding/4007035
# (plus more colors: https://invisible-island.net/ncurses/man/terminfo.5.html#h3-Color-Handling)
class termcolor:
    def _tput(s):
        try:
            return sp.check_output(['tput', *s.split()],
                                   stderr=sp.DEVNULL,
                                   text=True)
        except sp.CalledProcessError:
            return ''

    BOLD = _tput('bold')
    RESET = _tput('sgr0')
    # set ANSI foreground (setaf) colors
    BLACK = _tput('setaf 0')
    RED = _tput('setaf 1')
    GREEN = _tput('setaf 2')
    YELLOW = _tput('setaf 3')
    BLUE = _tput('setaf 4')
    MAGENTA = _tput('setaf 5')
    CYAN = _tput('setaf 6')
    WHITE = _tput('setaf 7')
    # High-intensity gray
    GRAY = _tput('setaf 8')

    del _tput


class DateRequester:
    """Request date from user.

    Basic usage (assuming you have a list/generator of panels)

        DateRequester(calendar.MONDAY, width).request(
            {p.date: p.get_rating(None) for p in panels}.items())

    The only two methods you should really care about:

        request(dates_and_ratings) -- takes a list of (date, rating) and
                                      returns the date user selected
        colorize_day(day_str, rating)
                                   -- returns the colored string of a
                                      panel's day string with ANSI escape
    """
    __slots__ = ('_cal', '_wrapper', '_input', '_output', '_error')

    def __init__(self, firstweekday=calendar.MONDAY, width=None,
                 input=input, output=print,
                 error=functools.partial(print, file=sys.stderr)):
        if width is None:
            width = shutil.get_terminal_size().columns
        self._input = input
        self._output = output
        self._error = error
        self._cal = calendar.TextCalendar(firstweekday)
        self._wrapper = textwrap.TextWrapper(width=width)

    def request(self, dates_and_ratings):
        return self._request_year(list(dates_and_ratings))

    def _request_year(self, values):
        years = sorted({date.year for date, rate in values})
        self._print_line('Select one year from the years below:')
        self._print_years(years)
        while True:
            y = self._read_line('Year: ').lower()
            if not y:
                continue
            if y in ('b', 'back', 'prev'):
                self._print_error('Error: cannot go back')
                continue
            if y.startswith('c'):
                args = y.split()
                if not (len(args) == 2
                        and args[0] in {'c', 'cal', 'calendar'}):
                    self._print_error('Error: invalid calendar command use')
                    continue
                try:
                    year = int(args[1])
                except ValueError:
                    self._print_error(f'Error: cannot parse calendar '
                                      f'year {y!r}...')
                    continue
                year_values = [(date, rate) for date, rate in values
                               if date.year == year]
                if self._check_year(year, years):
                    self._print_calendar_for_year(year, year_values)
                    self._output('')
                continue
            if y in ('p', 'pr', 'print'):
                self._print_years(years)
            try:
                year = int(y)
            except ValueError:
                self._print_error(f'Error: cannot parse year {y!r}...')
                continue
            if self._check_year(year, years):
                break

        year_values = [(date, rate) for date, rate in values
                       if date.year == year]
        self._output('')
        return self._request_month(values, year, year_values)

    # vibe check
    def _check_year(self, year, years):
        if year not in years:
            self._print_error(f'Error: {year} is not a valid year')
            return False
        return True

    def _request_month(self, values, year, year_values):
        months = sorted({date.month for date, rate in year_values})
        self._print_line(f'Select one month from the months of '
                         f'{year} below:')
        self._print_months(months)
        while True:
            m = self._read_line('Month: ').lower()
            if not m:
                continue
            if m in ('b', 'back', 'prev'):
                self._output('')
                return self._request_year(values)
            if m.startswith('c'):
                args = m.split()
                if not ((len(args) == 1 or len(args) == 2)
                        and args[0] in {'c', 'cal', 'calendar'}):
                    self._print_error('Error: invalid calendar command use')
                    continue
                if len(args) == 1:
                    self._print_calendar_for_year(year, year_values)
                    self._output('')
                else:
                    month = self._parse_month(args[1])
                    if self._check_month(args[1], month, months):
                        month_values = [(date, rate) for date, rate in
                                        year_values if date.month == month]
                        self._print_calendar_for_month(year, month,
                                                       month_values)
                continue
            if m in ('p', 'pr', 'print'):
                self._print_months(months)
                continue
            month = self._parse_month(m)
            if self._check_month(m, month, months):
                break

        month_values = [(date, rate) for date, rate in year_values
                        if date.month == month]
        self._output('')
        return self._request_day(values, year, year_values,
                                 month, month_values)

    def _parse_month(self, m_str):
        try:
            return int(m_str)
        except ValueError:
            pass
        for mo, month in enumerate(MONTH_NAMES, start=1):
            if m_str.startswith(month[:3].lower()):
                return mo
        # falsy number on failure
        return 0

    # vibe check 2
    def _check_month(self, m_str, month, months):
        if not month:
            self._print_error(f'Error: cannot parse month {m_str!r}')
            return False
        if month not in months:
            if 1 <= month <= 12:
                name = f' ({MONTH_ABBRS[month - 1]})'
            else:
                name = ''
            self._print_error(f'Error: {month}{name} is not a '
                              f'valid month')
            return False
        return True

    def _request_day(self, values, year, year_values, month, month_values):
        days = sorted({date.day for date, rate in month_values})
        self._print_line(
            f'Select one day from {MONTH_NAMES[month - 1]} '
            f'{year} below:')
        self._print_days(days)
        while True:
            d = self._read_line('Day: ').lower()
            if not d.strip():
                continue
            if d in ('b', 'back', 'prev'):
                self._output('')
                return self._request_month(values, year, year_values)
            if d in ('c', 'cal', 'calendar'):
                self._print_calendar_for_month(year, month, month_values)
                continue
            if d in ('p', 'pr', 'print'):
                self._print_days(days)
                continue
            try:
                day = int(d)
            except ValueError:
                self._print_error(f'Error: cannot parse day {d!r}...')
                continue
            if day not in days:
                self._print_error(f'Error: {day} is not a valid day')
            else:
                break
        return datetime.date(year, month, day)

    def _read_line(self, s):
        return self._input(s).strip()

    def _print_line(self, s):
        lines = self._wrapper.wrap(s)
        for line in lines:
            self._output(line)
        if len(lines) > 1:
            self._output('')

    def _print_error(self, s):
        lines = self._wrapper.wrap(s)
        for line in lines:
            self._error(line)
        if len(lines) > 1:
            self._error('')

    def _print_list(self, items, total_width, width, gap):
        # Compute number of columns we can fit, and no matter how narrow
        # the total width is we must have at least one column.
        col = max(1, total_width // (width+gap))
        col_count = 0
        gaps = ' ' * gap
        line_buf = []
        for item in items:
            line_buf.append(gaps)
            line_buf.append(f'{item:{width}}')
            col_count += 1
            if col_count == col:
                self._output(''.join(line_buf))
                line_buf.clear()
                col_count = 0
        # Only end the line if we are still in it
        if line_buf:
            self._output(''.join(line_buf))

    def _print_years(self, years):
        # 7 cols at most (7 * (4+3) = 49)
        width = self._wrapper.width
        self._print_list((f'{y:04}' for y in years),
                         min(49, width),
                         width=4,
                         gap=3)

    def _print_months(self, months):
        # Fit all months if we can, otherwise six at most.
        # (6 * (3+3) = 36)
        width = self._wrapper.width
        self._print_list((MONTH_ABBRS[mo - 1] for mo in months),
                         36 if 36 < width < 6 * len(months) else width,
                         width=3,
                         gap=3)

    def _print_days(self, days):
        # Fit 12 days at most?  (12 * (2+3) = 60)
        width = self._wrapper.width
        self._print_list((f'{d:2}' for d in days),
                         min(60, width),
                         width=2,
                         gap=3)

    def _print_calendar_for_year(self, year, year_values):
        #
        # Print calendars for each month like this:
        #
        #     Jan    Feb    Mar
        #     Apr    May    Jun
        #     Jul    Aug    Sep
        #     Oct    Nov    Dec
        #
        calendar_sep = ' ' * 4
        empty_line = ' ' * 20
        for start_month in (1, 4, 7, 10):
            if start_month != 1:
                self._output('')
            calendars = []
            for month in range(start_month, start_month + 3):
                values = [(date, rate) for date, rate in year_values
                          if date.month == month]
                calendars.append(self._format_calendar(year, month, values))
            # Traverse each line of every calendar and print them out,
            # filling any calendar with too few lines with empty_line
            for lines in itertools.zip_longest(
                    *[c.splitlines() for c in calendars],
                    fillvalue=empty_line):
                self._output(calendar_sep.join(lines).rstrip())

    def _print_calendar_for_month(self, year, month, values):
        cal = self._format_calendar(year, month, values)
        for line in cal.splitlines():
            self._output(line.rstrip())

    def _format_calendar(self, year, month, values):
        text = self._cal.formatmonth(year, month)
        lines = text.splitlines()
        assert all(date.year == year and date.month == month
                   for date, rate in values)
        sorted_values = sorted(values)
        # check for duplicate dates (maybe???)
        assert sorted_values == sorted(dict(values).items())
        # Make it so that every line is 20 characters long
        # (Also note that separating title from the body is necessary because
        # we don't want to replace anything there)
        title = f'{lines[0]:20}'
        body = '\n'.join(f'{line:20}' for line in lines[1:])
        # Create a list of substitutions to be made, with each item as
        # (index, replace_string)
        subs_list = []
        for date, rate in sorted_values:
            day_str = f'{date.day:2}'
            subs_str = self.color_day(day_str, rate)
            subs_list.append((body.index(day_str), subs_str))
        assert subs_list == sorted(subs_list)
        buf = []
        start = 0
        for index, repl in subs_list:
            buf.append(body[start:index])
            buf.append(repl)
            start = index + 2
        buf.append(body[start:])
        return title + '\n' + ''.join(buf)

    def color_day(self, day_str, rating):
        color = (termcolor.RED    if rating == ':(' else
                 termcolor.YELLOW if rating == ':|' else
                 termcolor.GREEN  if rating == ':)' else
                 termcolor.GRAY)
        return f'{termcolor.BOLD}{color}{day_str}{termcolor.RESET}'


def check_panel_attributes(values):
    """Check whether panels have the same attributes.

    This function takes a list of (panel, name) and returns an error
    string if it finds two panels with unequal/missing attributes.
    None is returned on success.
    """
    for (p1, s1), (p2, s2) in itertools.combinations(values, 2):
        assert p1.date == p2.date
        d1 = p1.get_attributes_for_comparison()
        d2 = p2.get_attributes_for_comparison()
        for key in d1.keys() | d2.keys():
            msg = None
            if not p2.has_attribute(key):
                value = p1.get_attribute(key)
                msg = (f'attribute {key!r} is found in {s1!r} '
                       f'(value {value!r}) but not in {s2!r}')
            elif not p1.has_attribute(key):
                value = p2.get_attribute(key)
                msg = (f'attribute {key!r} is found in {s2!r} '
                       f'(value {value!r}) but not in {s1!r}')
            else:
                value_1 = p1.get_attribute(key)
                value_2 = p2.get_attribute(key)
                if value_1 != value_2:
                    msg = (f'attribute {key!r} from {s1!r} differs from '
                           f'attribute from {s2!r} '
                           f'({value_1!r} != {value_2!r})')
            if msg is not None:
                yield (f'{len(values)} panels on {p1.date} have '
                       f'differing attributes: {msg}')


# Requires Python 3.5+
def load_module_from_file(modname, file):
    # Resolve the file path so that the module's __file__ attribute
    # is absolute
    file = os.path.realpath(file)
    # https://stackoverflow.com/a/67692
    spec = importlib.util.spec_from_file_location(modname, file)
    if spec is None:
        raise RuntimeError(f'failed to load module at {file!r}')
    module = importlib.util.module_from_spec(spec)
    # Put the module's parent directory at the very front in sys.path
    sys.path.insert(0, os.path.dirname(file))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module
