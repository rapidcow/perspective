"""Main program implementation"""

import argparse
from collections import defaultdict
import code
import calendar
import datetime
import io
import importlib.util
import itertools
import json
import os
import sys
import shutil
import tempfile
import textwrap

from ..__init__ import __version__
from ..timeutil import format_date
from ..stringify import PanelFormatter
from ..processors.json_processor import (JSONLoader, JSONDumper,
                                         load_json, dump_json, LoadError)
from .tools import load_module_from_file

__all__ = ['main', 'create_project']

CURDIR = os.path.dirname(__file__)
TEMPL = os.path.normpath(os.path.join(CURDIR, '..', '_templates'))


def main(argv):
    parser = argparse.ArgumentParser(
        prog='psp', description='psp library main program')
    parser.add_argument('--version', '-V', action='version',
                        version=f'%(prog)s {__version__}')
    parser.add_argument('--config', '-c',
        help='path to the Python configuration script')
    parser.add_argument('--wlevel', '-W', action='count', default=0,
        help=('warning level. 0 (default) for suppressing all warnings, '
              '1 for emitting warnings, 2 and above for raising warnings '
              'as exceptions'))
    parser.add_argument('--encoding', '-e', default='utf-8',
        help=("encoding used to read and write JSON backup files "
              "(default 'utf-8')"))

    # The required keyword argument was only added in Python 3.7...
    # could that be an issue?
    subparsers = parser.add_subparsers(dest='subname', required=True)

    # Options shared across 'print' and 'synopsis'
    # (See: https://stackoverflow.com/q/7498595)
    parser_file = argparse.ArgumentParser(add_help=False)
    file_group = parser_file.add_mutually_exclusive_group()
    # XXX: Don't make default None!  It breaks stuff when user tries to
    # supply only a --source/-s option
    file_group.add_argument('files', nargs='*', default=(),
        help=("backup files to load (default 'backup.json' if --source is "
              "not provided); cannot be provided if the --source option "
              "is present"))
    file_group.add_argument('--source', '-s',
        help=("a file containing source paths (relative to the file "
              "itself or absolute) to all backup files on each line; "
              "cannot be provided if the 'files' arguments are present"))

    # The 'print' subcommand
    parser_print = subparsers.add_parser(
        'print', help='print a panel', parents=[parser_file])
    # date is a str here and we expect BackupLoader.load_single()
    # to deal with it
    parser_print.add_argument('--date', '-d',
        help=('date of the panel to load (if you omit this, psp-print '
              'will ''prompt you to enter one progressively)'))
    parser_print.add_argument('--width', '-w', type=int,
        default=shutil.get_terminal_size().columns,
        help=('width of the panel to print (default is inferred from your '
              'terminal size, if possible, otherwise 80)'))
    parser_print.add_argument('--out', '-o',
        help='file name to print the panel to (default stdout)')

    # The 'synopsis' subcommand
    parser_synop = subparsers.add_parser(
        'synopsis', help='print a brief summary', parents=[parser_file])
    parser_synop.add_argument('--width', '-w', type=int,
        default=shutil.get_terminal_size().columns,
        help='width of the synopsis being printed')

    # The 'interact' subcommand
    parser_interact = subparsers.add_parser(
        'interact', help='launch an interactive prompt for testing',
        parents=[parser_file])

    parser_init = subparsers.add_parser(
        'init', help='create a backup project')
    parser_init.add_argument('target', nargs='?', default='.',
        help='path to the backup project')

    args = parser.parse_args(argv)

    if args.subname == 'init':
        os.mkdir(args.target)
        create_project(args.target)
        print(f'Created project at {args.target}')
        return

    sources = _get_source_files(parser, args)
    with tempfile.TemporaryDirectory() as tempdir:
        create_project(tempdir)
        del sys.modules['mystuff']
        with open(os.path.join(tempdir, 'scripts', 'main.py'),
                  'r+', encoding='utf-8') as fp:
            content = fp.read().replace(
                'import config\n',
                _import_relative('config', '.'),
            )
            fp.seek(0)
            # skipping truncation since everything is going to be
            # overwritten anyways
            fp.write(textwrap.dedent("""\
                import os
                import importlib.util
                """))
            fp.write(content)

        with open(os.path.join(tempdir, 'scripts', 'config.py'),
                  'r+', encoding='utf-8') as fp:
            content = fp.read().replace(
                    '    import mystuff\n',
                    textwrap.indent(
                        _import_relative('mystuff', '../lib'), ' ' * 4),
                ).replace(
                    '    import tools\n',
                    textwrap.indent(
                        _import_relative('tools', '../lib'), ' ' * 4),
                )
            fp.seek(0)
            fp.write(textwrap.dedent("""\
                import os
                import importlib.util
                """))
            fp.write(content)
            with open(os.path.join(TEMPL, 'extraconfig.py.txt')) as template:
                content = template.read().format(
                    config_path=args.config,
                    sources=sources,
                    warning_level=args.wlevel,
                    encoding=args.encoding)
                fp.write(content)
            fp.seek(0)

        main_mod = load_module_from_file(
            'main', os.path.join(tempdir, 'scripts', 'main.py'))
        config_mod = load_module_from_file(
            'config', os.path.join(tempdir, 'scripts', 'config.py'))

        if args.subname == 'print':
            new_args = ['print', '--width', str(args.width)]
            if args.date is not None:
                date = config_mod.parse_date(args.date)
                new_args.extend(['--date', format_date(date)])
            main_mod.main(new_args)

        elif args.subname == 'synopsis':
            main_mod.main(['synopsis', '--width', str(args.width)])

        elif args.subname == 'interact':
            if args.config is not None:
                config_user = load_module_from_file('config', args.config)
            else:
                config_user = None
            print('Loading panels... ', end='', flush=True)
            # At this point we should have overridden these functions
            # with extraconfig.py so that passing root directory (tempdir)
            # doesn't matter, but well... it doesn't hurt to still do it. :O
            panels = list(itertools.chain.from_iterable(
                config_mod.load_panels(file, base_dir)
                for file, base_dir, _ in
                config_mod.get_loading_info(tempdir)))
            merged = list(config_mod.load_merged_panels(tempdir))
            import pprint
            local = {
                # loaded panels
                'panels': panels,
                'merged': merged,
                # conveninent stuff
                'stdout': sys.stdout,
                'pp': pprint.pprint,
            }
            print('done')
            print(f'Launching an interacting prompt with the following '
                  f'variables:')
            print()
            if hasattr(config_user, 'BackupLoader'):
                print(f'    BackupLoader = {config_user.BackupLoader!r}')
                local['BackupLoader'] = config_user.BackupLoader
            if hasattr(config_user, 'PanelPrinter'):
                print(f'    PanelPrinter = {config_user.PanelPrinter!r}')
                local['PanelPrinter'] = config_user.PanelPrinter
            print(f'    panels = [list of length {len(panels)}]')
            print(f'    merged = [list of length {len(merged)}]')
            print(f'    stdout = sys.stdout')
            print(f'    pp = pprint.pprint')
            print()
            code.interact(local=local)


def create_project(project_dir):
    with open(os.path.join(TEMPL, 'main.py.txt'), encoding='utf-8') as fp:
        main_py = fp.read()
    with open(os.path.join(TEMPL, 'config.py.txt'), encoding='utf-8') as fp:
        config_py = fp.read()
    with open(os.path.join(TEMPL, 'mystuff.py.txt'), encoding='utf-8') as fp:
        mystuff_py = fp.read()

    scripts_dir = os.path.join(project_dir, 'scripts')
    lib_dir = os.path.join(project_dir, 'lib')
    os.mkdir(scripts_dir)
    os.mkdir(lib_dir)
    with open(os.path.join(scripts_dir, 'main.py'), 'x',
              encoding='utf-8') as fp:
        fp.write(main_py)
    with open(os.path.join(scripts_dir, 'config.py'), 'x',
              encoding='utf-8') as fp:
        fp.write(config_py)
    with open(os.path.join(lib_dir, 'mystuff.py'), 'x',
              encoding='utf-8') as fp:
        fp.write(mystuff_py)
    with open(os.path.join(scripts_dir, 'requirements.txt'), 'x',
              encoding='utf-8') as fp:
        fp.write(f'perspe=={__version__}\n')

    config_mod = load_module_from_file(
        'config', os.path.join(scripts_dir, 'config.py'))
    config_mod.dump_panels(project_dir, [])


def _import_relative(modname, parent):
    return textwrap.dedent(f"""\
        _im_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), {parent!r}, {modname + ".py"!r}))
        _im_spec = importlib.util.spec_from_file_location(
            {modname!r}, _im_file)
        if _im_spec is None:
            raise RuntimeError(f'failed to load module at {{_im_file!r}}')
        {modname} = importlib.util.module_from_spec(_im_spec)
        sys.path.insert(0, os.path.dirname(_im_file))
        try:
            _im_spec.loader.exec_module({modname})
        finally:
            sys.path.pop(0)
        """)


def _get_source_files(parser, args):
    source, files, encoding = args.source, args.files, args.encoding
    result = []
    if source:
        srcpath = os.path.abspath(source)
        dirpath = os.path.dirname(srcpath)
        with io.open(srcpath, encoding=encoding) as fp:
            for line in fp:
                name = line.rstrip('\n')
                if name:
                    filepath = os.path.join(dirpath, name)
                    result.append((os.path.normpath(filepath), name))
    else:
        for file in files:
            result.append((os.path.abspath(file), file))
    if not result:
        parser.print_usage(sys.stderr)
        print('psp: error: At least one file or --source must be provided',
              file=sys.stderr)
        sys.exit(1)
    return result
