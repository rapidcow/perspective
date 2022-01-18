"""Test the psp.timeutil module."""
from datetime import date, datetime, timezone
from textwrap import dedent
import unittest

from psp import stringify
from psp.types import Entry, Panel


class TestStringifyPanel(unittest.TestCase):
    def test_basics(self):
        panel = Panel(date(2022, 1, 18))
        time = datetime(2022, 1, 18, 13, 0, 0, tzinfo=timezone.utc)
        entry = Entry(panel, time)
        entry.set_data('Hello world!')
        formatter = stringify.PanelFormatter(width=33)
        self.assertEqual(
            formatter.format(panel),
            dedent(
            """\
                Tuesday, January 18, 2022


            1:00 PM
              Hello world!"""))

        panel.set_attribute('rating', ':)')
        self.assertEqual(
            formatter.format(panel),
            dedent(
            """\
              Tuesday, January 18, 2022  :)


            1:00 PM
              Hello world!"""))


class TestStringifyEntry(unittest.TestCase):
    pass
