"""Main program implementation"""

import argparse
import os

from .timeutil import parse_date
from .processors import load_json
from .stringify import stringify_panel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='?', default='backup.json',
                        help=("file path of the backup file "
                              "(default 'backup.json')"))
    parser.add_argument('date', type=parse_date,
                        help='date of the panel to load')
    parser.add_argument('--enc', '-e', metavar='ENCODING', default='utf-8',
                        help='encoding for opening the file')
    parser.add_argument('--width', '-w', type=int,
                        help='width of the printed panel')
    parser.add_argument('--24-hour', dest='time_format',
                        action='store_const', const='24 hour',
                        default='12 hour', help='24 hour format')
    parser.add_argument('--raise', '-r', dest='error', action='store_true',
                        help=('raise warnings while loading JSON '
                              '(sets JSONLoader.error_on_warning to True)'))
    parser.add_argument('--wrapper', '-t', default='textwrap',
                        choices=('textwrap', 'cjkwrap'),
                        help='text wrapper package to use')

    args = parser.parse_args()

    if args.width is None:
        import shutil
        width, _ = shutil.get_terminal_size()
    else:
        width = args.width

    with open(args.filename, encoding=args.enc) as fp:
        panel = load_json(fp, date=args.date, error_on_warning=args.error)
        # panels = load_json(fp, error_on_warning=args.error)

    if args.wrapper == 'textwrap':
        import textwrap
        wrapper = textwrap.TextWrapper()
    elif args.wrapper == 'cjkwrap':
        import cjkwrap
        wrapper = cjkwrap.CJKWrapper()

    # for panel in panels:
    #     if panel.date == args.date:
    #         print(stringify_panel(panel, wrapper=wrapper, width=width,
    #                               time_format=args.time_format))
    #         return
    # raise ValueError(f'date not found: {args.date}')

    print(stringify_panel(panel, wrapper=wrapper, width=width,
                          time_format=args.time_format))
