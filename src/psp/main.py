"""Main program implementation"""

import argparse
import datetime
import io
import itertools
import os
import shutil
import sys
import textwrap
if sys.version_info <= (3, 5):
    raise RuntimeError('Python 3.5+ is required to run psp as __main__')
import importlib.util

from .stringify import PanelFormatter
from .processors.json_processor import JSONLoader, JSONDumper
from .processors.json_processor import LoadError
from .timeutil import parse_date, to_utc
from .types import Panel, Entry

__all__ = ['main']


def get_terminal_width():
    return shutil.get_terminal_size().columns


def load_config_from_file(file):
    # Code from https://stackoverflow.com/a/67692
    spec = importlib.util.spec_from_file_location('config', file)
    config = importlib.util.module_from_spec(spec)
    # XXX: Why do we need this???
    sys.path.insert(1, os.path.dirname(file))
    try:
        spec.loader.exec_module(config)
    finally:
        sys.path.pop(1)
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help=
        'path to the Python configuration script')

    subparsers = parser.add_subparsers(required=True, dest='subname')

    # Options shared across 'print' and 'synopsis'
    # (See: https://stackoverflow.com/q/7498595)
    parser_file = argparse.ArgumentParser(add_help=False)
    file_group = parser_file.add_mutually_exclusive_group()
    file_group.add_argument('files', nargs='*', default=['backup.json'],
        help=("backup files to load (default 'backup.json'); cannot be "
              "provided if the --source option is present"))
    file_group.add_argument('--source', '-s', help=
        "source to all backup files; cannot be provided if "
        "the 'file' arguments are present")

    # The 'print' subcommand
    parser_print = subparsers.add_parser(
        'print', help='print a panel', parents=[parser_file])
    parser_print.add_argument('--date', '-d', type=parse_date, help=
        'date of the panel to load (if you omit this, psp-print will '
        'prompt you to enter one progressively)')
    parser_print.add_argument('--width', '-w', type=int,
        default=get_terminal_width(), help='width of the panel to print')
    parser_print.add_argument('--out', '-o', help=
        'file name to print the panel to (default stdout)')

    # The 'synopsis' subcommand
    parser_synop = subparsers.add_parser(
        'synopsis', help='print a brief summary', parents=[parser_file])

    # The 'checksum' subcommand
    parser_cksum = subparsers.add_parser(
        'checksum', help='generate a checksum')
    parser_cksum.add_argument(
        'cfile', help='backup file to generate checksum from')

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
                    filepath = os.path.join(dirpath, line.rstrip('\n'))
                    files.append(os.path.normpath(filepath))
        else:
            files.extend(args.files)

    if args.subname == 'print':
        loader = Loader()
        if args.date is None:
            # print all available dates
            num_files = len(files)
            plural = '' if num_files == 1 else 's'
            wrapper = textwrap.TextWrapper(width=get_terminal_width())
            print(wrapper.fill(
                'Welcome to the psp-print command-line utility!'))
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
        cwd = os.getcwd()
        for file in files:
            print(f'info {os.path.relpath(file, cwd)!r}:')
            loader.configure(base_dir=os.path.dirname(file),
                             suppress_warnings=True)
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
        loader = JSONLoader(base_dir=os.path.dirname(args.cfile), 
                            suppress_warning=True)
        panels = loader.load(args.cfile)
        p_count = 0
        e_count = 0
        size = 0
        for panel in panels:
            p_count += 1
            for entry in panel.entries():
                e_count += 1
                size += entry.get_raw_data_size()
        cksum_dict = OrderedDict(sorted({
            'panel': p_count,
            'entries': e_count,
            'total-bytes': size,
        }.items()))
        json.dump(cksum_dict, sys.stdout, indent=2)
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


def request_date_from_user(loader, files):
    """Input from sys.stdin"""
    width = get_terminal_width()
    need_space = True
    panels = {}
    for file in files:
        loader.configure(base_dir=os.path.dirname(file))
        try:
            _, pn = loader.load_all(file)
        except (ValueError, LoadError) as exc:
            raise RuntimeError(f'failed to load {file!r}') from exc
        panels.update((p.date, p) for p in pn)

    dates = set(panels.keys())
    return _get_year_from_user(dates, panels)


def _get_year_from_user(dates, panels, skip_single=True):
    width = get_terminal_width()
    years = sorted({d.year for d in dates})
    if len(years) == 1 and skip_single:
        need_space = False
        year = years.pop()
        print(f'You have only one year: {year}, automatically selecting it...')
    else:
        need_space = True
        print(f'Select one year from all the years below:')
        _print_list((str(y).zfill(4) for y in years), min(49, width), 4, 3)
        while True:
            y = input('Year: ')
            if not y.strip():
                continue
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
    return ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[m - 1]


def _get_month_from_user(dates, panels, year):
    width = get_terminal_width()
    year_dates = [d for d in dates if d.year == year]
    months = sorted({d.month for d in year_dates})
    if len(months) == 1:
        need_space = False
        month = months.pop()
        print(f'You have only one month in {year}: {month_name(month)}, '
              f'automatically selecting it...')
    else:
        need_space = True
        print(f'Select one month from the months of {year} below:')
        _print_list(map(month_name, months), min(48, width), 3, 3)
        while True:
            m = input('Month: ')
            if not m.strip():
                continue
            if m.lower() in ('b', 'back', 'prev'):
                print()
                return _get_year_from_user(dates, panels, year)
            month = 0
            try:
                month = int(m)
            except ValueError:
                pass
            if not month:
                for fmt in ('%b', '%B'):
                    try:
                        dt = datetime.datetime.strptime(m.strip(), fmt)
                        month = dt.month
                    except:
                        pass
                    else:
                        break
            if month:
                if month not in months:
                    print(f'Error: {month} ({month_name(month)}) is not a '
                          f'valid month')
                else:
                    break
            else:
                print(f'Error: cannot parse month {m!r}...', file=sys.stderr)

    if need_space:
        print()
    return _get_day_from_user(dates, panels, year, year_dates, month)


def _get_day_from_user(dates, panels, year, year_dates, month):
    width = get_terminal_width()
    month_dates = [d for d in year_dates if d.month == month]
    days = sorted({d.day for d in month_dates})
    if len(days) == 1:
        day = days.pop()
        print(f'You have only one day in {month_name(month)} {year}: {day}, '
              f'automatically selecting it...')
    else:
        print(f'Select one day from {month_name(month)} {year} below:')
        _print_list((format(d, '2') for d in days), min(72, width), 2, 3)
        while True:
            d = input('Day: ')
            if not d.strip():
                continue
            if d.lower() in ('b', 'back', 'prev'):
                print()
                return _get_month_from_user(dates, panels, year)
            if d.lower() in ('cal', 'calendar'):
                _print_calendar(year, month, days, panels)
                print()
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
    # Compute number of columns we can fit
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
    if col_count:
        print()


def _print_calendar(year, month, days, panels):
    import calendar
    text = calendar.TextCalendar().formatmonth(year, month)
    lines = text.splitlines()
    title = lines[0]
    body = '\n'.join(lines[1:])
    for day in days:
        this_date = datetime.date(year, month, day)
        try:
            panel = panels[this_date]
            rating = panel.get_attribute('rating')
            color = ('31' if rating == ':(' else    # Red
                     '33' if rating == ':|' else    # Yellow
                     '32' if rating == ':)' else    # Green
                     '30')                          # Black
            day_str = format(day, '2')
            body = body.replace(
                day_str, f'\033[1;{color}m{day_str}\033[0m', 1)
        except LookupError:
            pass
    print(title)
    print(body)


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
        raise ValueError(f'cannot find panel in the list of source '
                         f'files given {date}')
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
            entry.panel = merged_panel
    return merged_panel
