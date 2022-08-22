"""Test stuff in about.rst"""
# omg this is literally the most time-consuming test of them all

import contextlib
from textwrap import dedent
import io
import os
import sys
import tempfile
import unittest
import psp.main as main


def open_for_reading(file):
    return open(file, encoding='utf-8')


def open_for_writing(file):
    return open(file, 'x', encoding='utf-8')


class TestDemo(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def do_test_stdout(self, argv, cwd, expected):
        with io.StringIO() as stdout:
            with contextlib.redirect_stdout(stdout):
                oldcwd = os.getcwd()
                os.chdir(cwd)
                try:
                    main.main(argv)
                finally:
                    os.chdir(oldcwd)
            self.assertEqual(expected, stdout.getvalue(), msg=f'{argv!r}')

    def test_stuff(self):
        with tempfile.TemporaryDirectory() as root:
            with open_for_writing(os.path.join(root, 'backup.json')) as fp:
                fp.write(dedent("""\
                    {
                      "tz": "+08:00",
                      "data": [
                        {
                          "date": "2020-02-02",
                          "entries": [
                            {
                              "time": "06:00",
                              "data": "Hello world!"
                            },
                            {
                              "date-time": "2020-02-03 20:00",
                              "data": "Another entry from a different date!"
                            }
                          ]
                        }
                      ]
                    }
                    """))

            self.do_test_stdout(
                ['print', 'backup.json', '--date', '2020-02-02', '-w', '65'],
                root,
                dedent("""\
                =================================================================
                                    Sunday, February 2, 2020


                6:00 AM
                  Hello world!

                Feb  3   8:00 PM
                  Another entry from a different date!
                =================================================================
                """))

            del sys.modules['config']

            with open_for_writing(os.path.join(root, 'config.py')) as fp:
                fp.write(dedent("""\
                    from psp.stringify import PanelFormatter, EntryFormatter


                    class MyPanelFormatter(PanelFormatter):
                        def get_title(self, panel):
                            return super().get_title(panel).upper()


                    class MyEntryFormatter(EntryFormatter):
                        def get_basic_title(self, panel_date, entry_time):
                            return self.get_full_title(entry_time)


                    class PanelPrinter:
                        def __init__(self, width, root_dir):
                            self.formatter = MyPanelFormatter(width - 4,
                                                              time_format='24 hour',
                                                              title_entries_vsep=1,
                                                              entry_vsep=0)
                            entry_formatter = MyEntryFormatter(content_indent='> ')
                            self.formatter.set_entry_formatter(entry_formatter)

                        def print(self, panel, file):
                            cell_width = self.formatter.width
                            bar = '+-' + ('-' * cell_width) + '-+'
                            print(bar)
                            for line in self.formatter.wrap(panel):
                                print(f'| {line:{cell_width}} |', file=file)
                            print(bar)
                    """))

            self.do_test_stdout(
                ['--config', 'config.py', 'print', 'backup.json',
                 '--date', '2020-02-02', '-w', '65'],
                root,
                dedent("""\
                +---------------------------------------------------------------+
                |                   SUNDAY, FEBRUARY 2, 2020                    |
                |                                                               |
                | Feb  2, 2020   6:00                                           |
                | > Hello world!                                                |
                | Feb  3, 2020  20:00                                           |
                | > Another entry from a different date!                        |
                +---------------------------------------------------------------+
                """))

    def test_nasty_importlib_hacks(self):
        # What happens if "config" is in sys.modules?
        # That would completely break any "import config" statement
        # present in the temporarily created project scripts OnO;
        with tempfile.TemporaryDirectory() as root:
            with open_for_writing(os.path.join(root, 'backup.json')) as fp:
                fp.write(dedent("""\
                    {
                      "tz": "UTC",
                      "data": [
                        {
                          "date": "2022-08-10",
                          "entries": [
                            {
                              "time": "10:17",
                              "data": "test"
                            }
                          ]
                        }
                      ]
                    }
                    """))

            with open_for_writing(os.path.join(root, 'config.py')) as fp:
                fp.write(dedent("""\
                    from psp.stringify import PanelFormatter

                    class MyPF(PanelFormatter):
                        pass

                    _, checker = MyPF.remove_option('time_format')
                    MyPF.add_option('time_format', '24 hour', checker)
                    """))

            with open_for_writing(os.path.join(root, 'something.py')) as fp:
                fp.write(dedent("""\
                    from config import MyPF

                    class PanelPrinter:
                        __slots__ = ('formatter',)

                        def __init__(self, width, root_dir):
                            self.formatter = MyPF(width)

                        def print(self, panel, file):
                            print('=' * self.formatter.width, file=file)
                            print(self.formatter.format(panel), file=file)
                            print('=' * self.formatter.width, file=file)
                    """))

            self.do_test_stdout(
                ['-c=something.py', 'print', 'backup.json', '-d=2022-08-10',
                 '-w=32'],
                root,
                dedent("""\
                ================================
                   Wednesday, August 10, 2022


                10:17
                  test
                ================================
                """))


# Problem: when running the migrate command and the migration script
# contains imports from modules with name config/mystuff/tools
