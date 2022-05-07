"""Main program implementation"""

import argparse
import calendar
import datetime
import io
import itertools
import os
import shutil
import sys
import textwrap
# Make sure importlib trick works
if sys.version_info <= (3, 5):
    raise RuntimeError('Python 3.5+ is required to run psp as __main__')
import importlib.util

from .stringify import PanelFormatter
from .processors.json_processor import JSONLoader, JSONDumper
from .processors.json_processor import LoadError
from .timeutil import parse_date, to_utc
from .types import Panel

__all__ = ['main']


def get_terminal_width():
    # This should fall back to (columns=80, lines=24)
    return shutil.get_terminal_size().columns


def load_config_from_file(file):
    with open(file):    # Test for file existence
        pass
    # Code from https://stackoverflow.com/a/67692
    spec = importlib.util.spec_from_file_location('config', file)
    if spec is None:
        raise RuntimeError(f'failed to load configuration file {file!r}')
    config = importlib.util.module_from_spec(spec)
    # XXX: Why do we need this???
    sys.path.insert(1, os.path.dirname(file))
    try:
        spec.loader.exec_module(config)
    finally:
        sys.path.pop(1)
    return config


def get_date(s):
    if s.strip().lower() == 'today':
        return datetime.date.today()
    if s.strip().lower() == 'yesterday':
        return datetime.date.today() - datetime.timedelta(1)
    return parse_date(s)


def main():
    parser = argparse.ArgumentParser(
        prog='psp', description='psp library main program')
    parser.add_argument('--version', '-V', action='version',
                        version='%(prog)s pre-release')
    parser.add_argument('--config', '-c',
        help='path to the Python configuration script')
    parser.add_argument('--wlevel', '-w', action='count', default=0,
        help=('warning level. 0 (default) for suppressing all warnings, '
              '1 for emitting warnings, 2 and above for raising warnings '
              'as exceptions'))

    subparsers = parser.add_subparsers(required=True, dest='subname')

    # Options shared across 'print' and 'synopsis'
    # (See: https://stackoverflow.com/q/7498595)
    parser_file = argparse.ArgumentParser(add_help=False)
    file_group = parser_file.add_mutually_exclusive_group()
    file_group.add_argument('files', nargs='*', default=['backup.json'],
        help=("backup files to load (default 'backup.json' if --source is "
              "not provided); cannot be provided if the --source option "
              "is present"))
    file_group.add_argument('--source', '-s',
        help=("a file containing source paths (relative to the file "
              "itself or absolute) to all backup files on each line; "
              "cannot be provided if the 'file' arguments are present"))

    # The 'print' subcommand
    parser_print = subparsers.add_parser(
        'print', help='print a panel', parents=[parser_file])
    parser_print.add_argument('--date', '-d', type=get_date, help=
        'date of the panel to load (if you omit this, psp-print will '
        'prompt you to enter one progressively)')
    parser_print.add_argument('--width', '-w', type=int,
        default=get_terminal_width(), help=
        'width of the panel to print (default is inferred from your '
        'terminal size, if possible, otherwise 80)')
    parser_print.add_argument('--out', '-o', help=
        'file name to print the panel to (default stdout)')

    # The 'synopsis' subcommand
    parser_synop = subparsers.add_parser(
        'synopsis', help='print a brief summary', parents=[parser_file])

    # The 'checksum' subcommand
    parser_cksum = subparsers.add_parser(
        'checksum', help='generate a checksum')
    parser_cksum.add_argument(
        'cfile', nargs='?', default='backup.json',
        help='backup file to generate checksum from')

    # The 'merge' subcommand
    parser_merge = subparsers.add_parser(
        'merge', help='merge two or more backup files')
    parser_merge.add_argument('outfile')
    parser_merge.add_argument('infile', nargs='+')

    args = parser.parse_args()

    if args.config is not None:
        config = load_config_from_file(args.config)
    else:
        config = None

    # Get backup loader class
    try:
        Loader = config.BackupLoader
    except AttributeError:
        Loader = JSONLoader

    # Get backup dumper class
    try:
        Dumper = config.BackupDumper
    except AttributeError:
        class Dumper(JSONDumper):
            def __init__(self, base_dir):
                super().__init__(base_dir=base_dir)

    # Get panel printer class
    try:
        Printer = config.PanelPrinter
    except AttributeError:
        class Printer:
            __slots__ = ('formatter',)

            def __init__(self, width):
                self.formatter = PanelFormatter(width)

            def print(self, panel, file):
                print(self.formatter.format(panel), file=file)

    if args.subname in {'print', 'synopsis'}:
        files = []
        if args.source is not None:
            srcpath = os.path.abspath(args.source)
            dirpath = os.path.dirname(srcpath)
            with io.open(srcpath) as fp:
                for line in fp:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    filepath = os.path.join(dirpath, line.rstrip('\n'))
                    files.append(os.path.normpath(filepath))
        else:
            files.extend(args.files)

    if args.subname == 'print':
        loader = Loader()
        set_warning_level(loader, args.wlevel)
        if args.date is None:
            # print all available dates
            num_files = len(files)
            plural = '' if num_files == 1 else 's'
            wrapper = textwrap.TextWrapper(width=get_terminal_width())
            lines = wrapper.wrap(
                'Welcome to the psp-print command-line utility!')
            for line in lines:
                print(line)
            if len(lines) > 1:
                print()
            print(wrapper.fill(
                f"I'm about to load from the {num_files} file{plural} you "
                f"specified, so let me know what panel you would like to "
                f"display..."))
            print()
            date = request_date_from_user(loader, files)
            print()
        else:
            date = args.date
        panel = load_panel_with_date(loader, files, date)
        printer = Printer(args.width)
        if args.out is None:
            printer.print(panel, sys.stdout)
        else:
            with open(args.out, 'w') as fp:
                printer.print(panel, fp)
    elif args.subname == 'synopsis':
        big_p_count = 0
        big_e_count = 0
        wrapper = textwrap.TextWrapper(
            width=max(5, get_terminal_width() - 4))
        loader = Loader()
        set_warning_level(loader, args.wlevel)
        cwd = os.getcwd()
        for file in files:
            print(f'info {os.path.relpath(file, cwd)!r}:')
            loader.configure(base_dir=os.path.dirname(file))
            attrs, panels = loader.load_all(file)
            if any(attrs.get('desc', '')):
                print('  description:')
                desc = (attrs['desc'] if isinstance(attrs['desc'], str)
                        else ''.join(attrs['desc']))
                for par in desc.splitlines():
                    lines = wrapper.wrap(par) or ['']
                    for line in lines:
                        print(('    ' + line).rstrip())
            p_count = len(panels)
            e_count = sum(1 for p in panels for e in p.entries())
            print('  panels:', p_count)
            print('  entries:', e_count)
            big_p_count += p_count
            big_e_count += e_count
        print('total:')
        print('  panels:', big_p_count)
        print('  entries:', big_e_count)
    elif args.subname == 'merge':
        raise RuntimeError('psp-merge coming soon!')
    elif args.subname == 'checksum':
        import json
        from collections import OrderedDict
        loader = Loader()
        loader.configure(base_dir=os.path.dirname(args.cfile))
        set_warning_level(loader, args.wlevel)
        _, panels = loader.load_all(args.cfile)
        p_count = 0
        e_count = 0
        size = 0
        for panel in panels:
            p_count += 1
            for entry in panel.entries():
                e_count += 1
                size += entry.get_raw_data_size()
        cksum_dict = OrderedDict([
            ('panel', p_count),
            ('entries', e_count),
            ('total-bytes', size)])
        json.dump(cksum_dict, sys.stdout, indent=2, sort_keys=False)
        print('\n', flush=True)  # i don't know why
        while True:
            inp = input('Add this to backup? (y/[n]) ')
            if not inp or inp == 'n':
                break
            elif inp == 'y':
                with open(args.cfile) as fp:
                    data = json.load(fp, object_pairs_hook=OrderedDict)
                new_data = OrderedDict()
                new_data['checksum'] = cksum_dict
                new_data.update(data)
                with open(args.cfile, 'w') as fp:
                    json.dump(new_data, fp, indent=2, sort_keys=False)
                break
    else:
        assert False, 'unreachable'


def set_warning_level(loader, level):
    loader.configure(suppress_warnings=level == 0,
                     error_on_warning=level >= 2)


def request_date_from_user(loader, files):
    """Input from sys.stdin"""
    width = get_terminal_width()
    need_space = True
    panels = {}
    for file in files:
        loader.configure(base_dir=os.path.dirname(file))
        try:
            _, panel_objects = loader.load_all(file)
        except (ValueError, LoadError) as exc:
            raise RuntimeError(f'failed to load {file!r}') from exc
        panels.update((p.date, p) for p in panel_objects)

    dates = set(panels.keys())
    return _get_year_from_user(dates, panels)


def _get_year_from_user(dates, panels, skip_one=True):
    width = get_terminal_width()
    wrapper = textwrap.TextWrapper(width)
    years = sorted({d.year for d in dates})
    if len(years) == 1 and skip_one:
        need_space = False
        year = years.pop()
        print(wrapper.fill(
            f'Only one year found: {year}, automatically selecting it...'))
    else:
        need_space = True
        print(wrapper.fill(
            f'Select one year from all the years below:'))
        _print_list((str(y).zfill(4) for y in years), min(49, width), 4, 3)
        while True:
            y = input('Year: ')
            if not y.strip():
                continue
            if y.lower() in ('p', 'print'):
                _print_list((str(y).zfill(4) for y in years),
                            min(49, width), 4, 3)
            try:
                year = int(y)
            except ValueError:
                print(f'Error: cannot parse year {y!r}...', file=sys.stderr)
            else:
                if year not in years:
                    print(f'Error: {year} is not a valid year', file=sys.stderr)
                else:
                    break

    if need_space:
        print()
    return _get_month_from_user(dates, panels, year)


def month_name(m):
    return ('January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November',
            'December')[m - 1]


def month_abbr(m):
    return month_name(m)[:3]


def _get_month_from_user(dates, panels, year, skip_one=True):
    width = get_terminal_width()
    wrapper = textwrap.TextWrapper(width)
    year_dates = [d for d in dates if d.year == year]
    months = sorted({d.month for d in year_dates})
    if len(months) == 1 and skip_one:
        need_space = False
        month = months.pop()
        print(wrapper.fill(
            f'Only one month in {year} found: {month_name(month)}, '
            f'automatically selecting it...'))
    else:
        need_space = True
        print(wrapper.fill(
            f'Select one month from the months of {year} below:'))
        # Fit all months if we can, otherwise six at most.
        _print_list(map(month_abbr, months),
                    36 if 36 < width < 6 * len(months) else width,
                    3, 3)
        while True:
            m = input('Month: ')
            if not m.strip():
                continue
            if m.lower() in ('b', 'back', 'prev'):
                print()
                return _get_year_from_user(dates, panels, False)
            month = 0
            if m.lower() in ('c', 'cal', 'calendar'):
                _print_calendar_for_year(year, panels)
                print()
                continue
            if m.lower() in ('p', 'print'):
                _print_list(
                    map(month_abbr, months),
                    36 if 36 < width < 6 * len(months) else width,
                    3, 3)
                continue
            try:
                month = int(m)
            except ValueError:
                pass
            if not month:
                for fmt in ('%b', '%B'):
                    try:
                        dt = datetime.datetime.strptime(m.strip(), fmt)
                        month = dt.month
                    except ValueError:
                        pass
                    else:
                        break
            if month:
                if month not in months:
                    if 1 <= month <= 12:
                        name = f' ({month_abbr(month)})'
                    else:
                        name = ''
                    print(f'Error: {month}{name} is not a valid month')
                else:
                    break
            else:
                print(f'Error: cannot parse month {m!r}...', file=sys.stderr)

    if need_space:
        print()
    return _get_day_from_user(dates, panels, year, year_dates, month)


def _get_day_from_user(dates, panels, year, year_dates, month):
    width = get_terminal_width()
    wrapper = textwrap.TextWrapper(width)
    month_dates = [d for d in year_dates if d.month == month]
    days = sorted({d.day for d in month_dates})
    if len(days) == 1:
        day = days.pop()
        print(wrapper.fill(
            f'You have only one day in {month_name(month)} {year}: '
            f'{day}, automatically selecting it...'))
    else:
        print(wrapper.fill(
            f'Select one day from {month_name(month)} {year} below:'))
        # Fit 12 days at most?
        _print_list((format(d, '2') for d in days), min(60, width), 2, 3)
        while True:
            d = input('Day: ')
            if not d.strip():
                continue
            if d.lower() in ('b', 'back', 'prev'):
                print()
                return _get_month_from_user(dates, panels, year, False)
            if d.lower() in ('c', 'cal', 'calendar'):
                _print_calendar(year, month, days, panels)
                print()
                continue
            if d.lower() in ('p', 'print'):
                _print_list((format(d, '2') for d in days), min(60, width),
                            2, 3)
                continue
            try:
                day = int(d)
            except ValueError:
                print(f'Error: cannot parse day {d!r}...', file=sys.stderr)
            else:
                if day not in days:
                    print(f'Error: {day} is not a valid day')
                else:
                    break

    return datetime.date(year, month, day)


def _print_list(items, total_width, width, gap):
    # Compute number of columns we can fit, and no matter how narrow
    # the total width is we must have at least one column.
    col = max(1, total_width // (width+gap))
    col_count = 0
    gaps = ' ' * gap
    for item in items:
        print(gaps, end='')
        print(format(item, str(width)), end='')
        col_count += 1
        if col_count == col:
            print()
            col_count = 0
    # Only end the line if we are still printing one
    if col_count:
        print()


def _format_calendar(year, month, days, panels):
    text = calendar.TextCalendar().formatmonth(year, month)
    lines = text.splitlines()
    # Make it so that every line is 20 characters long
    # (Also note that separating title from the body is necessary because
    # we don't want to replace anything there)
    title = format(lines[0], '20')
    body = '\n'.join(format(line, '20') for line in lines[1:])
    # Create a list of substitutions to be made, with each item as
    # (index, replace_string)
    subs_list = []
    for day in days:
        this_date = datetime.date(year, month, day)
        panel = panels[this_date]
        try:
            rating = panel.get_attribute('rating')
        except KeyError:
            pass
        else:
            color = ('31' if rating == ':(' else    # Red
                     '33' if rating == ':|' else    # Yellow
                     '32' if rating == ':)' else    # Green
                     '30')                          # Black
            # right-padded number of width 2
            day_str = format(day, '2')
            subs_str = f'\033[1;{color}m{day_str}\033[0m'
            subs_list.append((body.index(day_str), subs_str))
    subs_list.sort()
    buf = []
    start = 0
    for index, repl in subs_list:
        buf.append(body[start:index])
        buf.append(repl)
        start = index + 2
    buf.append(body[start:])
    return title + '\n' + ''.join(buf)


def _print_calendar(year, month, days, panels):
    text_lines = _format_calendar(year, month, days, panels)
    for line in text_lines.splitlines():
        print(line.rstrip())


def _print_calendar_for_year(year, panels):
    #
    # Print calendars for each month like this:
    #
    #     Jan    Feb    Mar
    #     Apr    May    Jun
    #     Jul    Aug    Sep
    #     Oct    Nov    Dec
    #
    not_first_row = False
    calendar_sep = ' ' * 4
    empty_row = ' ' * 20
    for start_month in [1, 4, 7, 10]:
        if not_first_row:
            print()
        calendars = []
        for month in range(start_month, start_month + 3):
            days = {pdate.day for pdate in panels.keys()
                    if pdate.year == year and pdate.month == month}
            calendars.append(_format_calendar(year, month, days, panels))
        # Traverse each line of every calendar and print them out
        for lines in itertools.zip_longest(
                *[c.splitlines() for c in calendars],
                fillvalue=empty_row):
            print(calendar_sep.join(lines).rstrip())
        not_first_row = True


def load_panel_with_date(loader, files, date):
    panels = []
    for file in files:
        try:
            loader.configure(base_dir=os.path.dirname(file))
            panel = loader.load_single(file, date)
        except (ValueError, LookupError):
            continue
        if panel is not None:
            panels.append(panel)
    if not panels:
        raise ValueError(f'cannot find panel {date} in the given list of '
                         f'source files, or a fatal error occured while '
                         f'loading some of the backup files')
    # Pick any combination of two panels and check if they have the
    # exact same attributes; if not then throw a warning
    for p1, p2 in itertools.combinations(panels, 2):
        if p1.get_attribute_dict() != p2.get_attribute_dict():
            import warnings
            warnings.warn(f'{len(panels)} panels found for {date} have '
                          f'different attributes; the printed information '
                          f'might be inconsistent', RuntimeWarning)
            break
    # Create a new panel
    merged_panel = Panel.from_panel(panels[0])
    # Set the panel of each entry to the new panel
    for panel in panels:
        # Iterating over a copy of the entries list is necessary!
        for entry in panel.get_entries():
            merged_panel.add_entry(entry)
    return merged_panel
