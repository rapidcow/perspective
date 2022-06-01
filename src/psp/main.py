"""Main program implementation"""

import argparse
import calendar
import datetime
import io
import itertools
import json
import os
import sys
import textwrap
# Make sure importlib trick works
if sys.version_info < (3, 5):
    raise RuntimeError('Python 3.5+ is required to run psp as __main__')
import importlib.util

from .stringify import PanelFormatter
from .processors.json_processor import JSONLoader, JSONDumper
from .processors.json_processor import LoadError
from .timeutil import parse_date
from .types import Panel
from . import util

__all__ = ['main']


def get_terminal_width():
    import shutil
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def load_config_from_file(file):
    # Resolve the file path otherwise the __file__ attribute is relative
    file = os.path.realpath(file)
    # Code from https://stackoverflow.com/a/67692
    spec = importlib.util.spec_from_file_location('config', file)
    if spec is None:
        raise RuntimeError(f'failed to load configuration file {file!r}')
    config = importlib.util.module_from_spec(spec)
    # Put the module in search path I guess
    sys.path.insert(0, os.path.dirname(file))
    try:
        spec.loader.exec_module(config)
    finally:
        sys.path.pop(0)
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
                        version='%(prog)s 0.1.1')
    parser.add_argument('--config', '-c',
        help='path to the Python configuration script')
    parser.add_argument('--wlevel', '-w', action='count', default=0,
        help=('warning level. 0 (default) for suppressing all warnings, '
              '1 for emitting warnings, 2 and above for raising warnings '
              'as exceptions'))
    parser.add_argument('--encoding', '-e', default='utf-8',
        help=("encoding used to read and write JSON backup files "
              "(default 'utf-8')"))

    subparsers = parser.add_subparsers(required=True, dest='subname')

    # Options shared across 'print' and 'synopsis'
    # (See: https://stackoverflow.com/q/7498595)
    parser_file = argparse.ArgumentParser(add_help=False)
    file_group = parser_file.add_mutually_exclusive_group()
    file_group.add_argument('files', nargs='*', default=('backup.json',),
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

    # The 'merge' subcommand
    parser_merge = subparsers.add_parser(
        'merge', help='merge two or more backup files', parents=[parser_file])
    parser_merge.add_argument('out', help='output directory')

    args = parser.parse_args()

    if args.config is not None:
        config = load_config_from_file(args.config)
    else:
        config = None

    # Get backup loader class
    try:
        Loader = config.BackupLoader
    except AttributeError:
        class Loader(JSONLoader):
            __slots__ = ()

            def configure(self, **kwargs):
                super().configure(**kwargs)

            def load_json(self, file, encoding):
                with open(file, encoding=encoding) as fp:
                    return json.load(fp)

            def load_all(self, data):
                return super().load_data(data)

            def load_single(self, data, date):
                return super().load_data(data, date=date)

    # Get backup dumper class
    try:
        Dumper = config.BackupDumper
    except AttributeError:
        class Dumper(JSONDumper):
            __slots__ = ()

            # The configure() method is not needed (I think)

            def dump(self, panels, dirname, encoding):
                super().dump(panels, dirname, encoding=encoding)

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
        files = get_source_files(args.source, args.files)
    elif args.subname == 'merge':
        files = get_source_files(args.source, args.files)

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
            date = request_date_from_user(loader, args.encoding, files)
            print()
        else:
            date = args.date
        panel = load_panel_with_date(loader, args.encoding, files, date,
                                     args.wlevel)
        printer = Printer(args.width)
        if args.out is None:
            printer.print(panel, sys.stdout)
        else:
            with open(args.out, 'w', encoding=args.encoding) as fp:
                printer.print(panel, fp)

    elif args.subname == 'synopsis':
        from collections import defaultdict
        loader = Loader()
        set_warning_level(loader, args.wlevel)
        wrapper = textwrap.TextWrapper(
            width=max(5, get_terminal_width() - 4))
        cwd = os.getcwd()
        panel_map = defaultdict(list)
        for file in files:
            rpath = os.path.relpath(file, cwd)
            print(f'info {rpath!r}:')
            loader.configure(base_dir=os.path.dirname(file))
            data = loader.load_json(file, args.encoding)
            panels = loader.load_all(data)
            if any(data.get('desc', '')):
                print('  description:')
                desc = (data['desc'] if isinstance(data['desc'], str)
                        else ''.join(data['desc']))
                for par in desc.splitlines():
                    lines = wrapper.wrap(par) or ['']
                    for line in lines:
                        print(('    ' + line).rstrip())
            print('  panels:', len(panels))
            print('  entries:', sum(1 for p in panels for e in p.entries()))
            for panel in panels:
                panel_map[panel.date].append((panel, rpath))

        merged = merge_panel_map(panel_map, 0)
        print('total:')
        print('  panels: {} ({} after merging)'.format(
            sum(len(panels) for panels in panel_map.values()),
            len(merged)))
        print('  entries: {}'.format(
            sum(1 for panel in merged for entry in panel.get_entries())))

    elif args.subname == 'merge':
        from collections import defaultdict
        loader = Loader()
        dumper = Dumper()
        set_warning_level(loader, args.wlevel)
        panel_map = defaultdict(list)
        cwd = os.getcwd()
        plural = '' if len(files) == 1 else 's'
        print(f'loading files from {len(files)} file{plural}... ', end='',
              flush=True)
        for file in files:
            loader.configure(base_dir=os.path.dirname(file))
            data = loader.load_json(file, args.encoding)
            panels = loader.load_all(data)
            rpath = os.path.relpath(file, cwd)
            for panel in panels:
                panel_map[panel.date].append((panel, rpath))
        print('done')

        panel_num = sum(len(panels) for panels in panel_map.values())
        plural = '' if panel_num == 1 else 's'
        print(f'merging {panel_num} panel{plural}... ', end='', flush=True)
        merged = merge_panel_map(panel_map, args.wlevel)
        print(f'done ({len(merged)} after merging)')
        merged.sort(key=lambda p: p.date)
        print(f'exporting to {args.out!r}... ', end='', flush=True)
        dumper.dump(merged, args.out, args.encoding)
        print('done')
    else:
        raise RuntimeError('unreachable')


def get_source_files(source, files):
    result = []
    if source is not None:
        srcpath = os.path.abspath(source)
        dirpath = os.path.dirname(srcpath)
        with io.open(srcpath) as fp:
            for line in fp:
                # Skip empty lines
                if not line.strip():
                    continue
                filepath = os.path.join(dirpath, line.rstrip('\n'))
                result.append(os.path.normpath(filepath))
    else:
        result.extend(files)
    return result


def set_warning_level(loader, level):
    loader.configure(suppress_warnings=level == 0,
                     error_on_warning=level >= 2)


def request_date_from_user(loader, encoding, files):
    """Input from sys.stdin"""
    panels = {}
    for file in files:
        loader.configure(base_dir=os.path.dirname(file))
        try:
            data = loader.load_json(file, encoding)
            panel_objects = loader.load_all(data)
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
        print(wrapper.fill('Select one year from the years below:'))
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
    name = month_name(m)
    return name[:3 if len(name) > 4 else 4]


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
    for start_month in (1, 4, 7, 10):
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


def load_panel_with_date(loader, encoding, files, date, wlevel):
    panels = []
    sources = []
    cwd = os.getcwd()
    for file in files:
        loader.configure(base_dir=os.path.dirname(file))
        data = loader.load_json(file, encoding)
        try:
            panel = loader.load_single(data, date)
        except LookupError:
            continue
        except Exception as exc:
            raise RuntimeError(f'failed to load {file!r}') from exc
        if panel is not None:
            panels.append(panel)
            sources.append(os.path.relpath(file, cwd))
    if not panels:
        raise ValueError(f'cannot find panel {date} in the given list of '
                         f'source files')
    check_panels_equal(date, panels, sources, wlevel)
    merged_panel = util.merge_panels(panels)
    merged_panel.sort_entries(key=lambda e: e.date_time)
    merged_panel.sort_entries(key=lambda e: e.insight)
    return merged_panel


def check_panels_equal(date, panels, sources, wlevel):
    """Warn if any pair of panels have unequal attributes."""
    # Pick any combination of two panels and check if they have the
    # exact same attributes; if not then throw a warning
    for (p1, s1), (p2, s2) in itertools.combinations(zip(panels, sources), 2):
        d1 = p1.get_attribute_dict()
        d2 = p2.get_attribute_dict()
        for key in d1.keys() | d2.keys():
            msg = None
            if not p2.has_attribute(key):
                msg = (f'attribute {key!r} is found in {s1!r} but '
                       f'not in {s2!r}')
            elif not p1.has_attribute(key):
                msg = (f'attribute {key!r} is found in {s2!r} but '
                       f'not in {s1!r}')
            else:
                value_1 = p1.get_attribute(key)
                value_2 = p2.get_attribute(key)
                if value_1 != value_2:
                    msg = (f'attribute {key!r} from {s1!r} differs from '
                           f'attribute from {s2!r} '
                           f'({value_1!r} != {value_2!r})')
            if msg is not None:
                errmsg = (f'panels on {date} have differing '
                          f'attributes: {msg}')
                if wlevel >= 2:
                    raise RuntimeError(errmsg)
                elif wlevel >= 1:
                    import warnings
                    warnings.warn(errmsg, RuntimeWarning)
                    break


def merge_panel_map(panel_map, wlevel):
    merged = []
    for date, panels_and_sources in panel_map.items():
        panels, sources = zip(*panels_and_sources)
        check_panels_equal(date, panels, sources, wlevel)
        merged.append(util.merge_panels(panels))
    return merged
