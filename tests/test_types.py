"""Test the psp.types module."""
from random import randint
from datetime import date, datetime, timezone, timedelta
import unittest

from psp.types import Entry, Panel


class TestPanel(unittest.TestCase):
    def test_repr(self):
        panel_date = date(2021, 12, 25)
        panel = Panel(panel_date)
        self.assertEqual(repr(panel), f'<Panel object on {panel_date}>')

    def test_entries(self):
        panel = Panel(date(2021, 12, 17))

        tz = timezone(timedelta(hours=randint(-12, 12)))
        entry1 = Entry(datetime(2021, 12, 17, 13, 00, tzinfo=tz))
        entry1.set_data('first entry')

        entry2 = Entry(datetime(2021, 12, 17, 15, 20, tzinfo=tz))
        entry2.set_data('second entry')
        panel.add_entries([entry1, entry2])

        entries = panel.get_entries()
        self.assertEqual(entries, [entry1, entry2])
        self.assertIs(entry1.panel, panel)
        self.assertIs(entry2.panel, panel)


class TestEntry(unittest.TestCase):
    def test_repr(self):
        panel = Panel(date(2020, 2, 2))
        entry_time = datetime(2020, 2, 2, 14, 14, tzinfo=timezone.utc)
        entry = Entry(entry_time)
        panel.add_entry(entry)
        self.assertEqual(repr(entry), f'<Entry object at {entry_time}>')
        self.assertIn(entry, panel.get_entries())
        self.assertIs(entry.panel, panel)

    def test_validation(self):
        panel_date = date(2019, 8, 25)
        panel = Panel(panel_date)
        msg = 'date_time should be an aware datetime object'
        with self.assertRaises(TypeError, msg=msg):
            Entry(datetime(2019, 8, 25, 10))

        entry_time = datetime(2019, 8, 24, 23, 59, 59, tzinfo=timezone.utc)
        entry = Entry(entry_time)
        msg = ('entry time ({}) earlier than start of day of the parent '
               'panel ({}) in local time').format(entry_time, panel_date)
        with self.assertRaises(ValueError, msg=msg):
            panel.add_entry(entry)

        entry_time += timedelta(days=2)
        entry = Entry(entry_time, insight=True)
        msg = ('entry is an insight and its time ({}) is less than '
               '2 days apart from the start of day of the parent panel '
               '({}) in local time').format(entry_time, panel_date)
        with self.assertRaises(ValueError, msg=msg):
            panel.add_entry(entry)

    def test_metadata(self):
        # metadata validation (created, posted, filename, ...)
        pass
