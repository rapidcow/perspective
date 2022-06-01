"""Test the psp.types module."""
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

        tz = timezone(timedelta(hours=-8))
        entry1 = Entry(datetime(2021, 12, 17, 13, 0, tzinfo=tz))
        entry1.set_data('first entry')

        entry2 = Entry(datetime(2021, 12, 17, 15, 20, tzinfo=tz))
        entry2.set_data('second entry')
        panel.add_entry(entry1)
        panel.add_entry(entry2)

        entries = panel.get_entries()
        self.assertEqual(entries, [entry1, entry2])
        self.assertIs(entry1.panel, panel)
        self.assertIs(entry2.panel, panel)

    def test_count(self):
        panel = Panel(date(2022, 2, 2))
        self.assertEqual(panel.count(), 0)
        for i in range(24):
            tz = timezone(timedelta(hours=-i))
            entry1 = Entry(datetime(2022, 2, 2, i, 0, tzinfo=tz))
            panel.add_entry(entry1)
        self.assertEqual(panel.count(), 24)


class TestEntry(unittest.TestCase):
    def test_repr(self):
        panel = Panel(date(2020, 2, 2))
        entry_time = datetime(2020, 2, 2, 14, 14, tzinfo=timezone.utc)
        entry = Entry(entry_time)
        panel.add_entry(entry)
        self.assertEqual(repr(entry), f'<Entry object at {entry_time}>')
        self.assertEqual(panel.get_entries(), [entry])
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
        entry.date_time += timedelta(minutes=1)
        panel.add_entry(entry)

        entry_time += timedelta(days=2)
        entry = Entry(entry_time, insight=True)
        msg = ('entry is an insight and its time ({}) is less than '
               '2 days apart from the start of day of the parent panel '
               '({}) in local time').format(entry_time, panel_date)
        with self.assertRaises(ValueError, msg=msg):
            panel.add_entry(entry)
        entry.date_time += timedelta(minutes=1)
        panel.add_entry(entry)

    def test_setting_panel(self):
        """Test if Panel.add_entry() and Panel.remove_entry() work properly
        and if entry time & insight validation works when the panel is
        changed.
        """
        panel_1 = Panel(date(2022, 5, 10))
        panel_2 = Panel(date(2022, 5, 12))
        entry_1 = Entry(datetime(2022, 5, 11, 23, 59, tzinfo=timezone.utc))
        entry_2 = Entry(datetime(2022, 5, 13, 23, 59, tzinfo=timezone.utc))
        entry_2.insight = True

        self.assertFalse(entry_1.has_panel())
        self.assertFalse(entry_2.has_panel())

        # ENTRY 1
        panel_1.add_entry(entry_1)
        # Changing panel for regular entry
        with self.assertRaises(ValueError):
            panel_2.add_entry(entry_1)
        # panel_1.remove_entry() should be successfully called
        self.assertFalse(entry_1.has_panel())
        self.assertEqual(panel_1.get_entries(), [])

        entry_1.date_time += timedelta(minutes=1)
        panel_2.add_entry(entry_1)

        self.assertIs(entry_1.panel, panel_2)
        self.assertEqual(panel_1.get_entries(), [])
        self.assertEqual(panel_2.get_entries(), [entry_1])
        panel_2.remove_entry(entry_1)
        self.assertEqual(panel_2.get_entries(), [])

        # ENTRY 2
        panel_1.add_entry(entry_2)
        # Changing panel for insight entry
        with self.assertRaises(ValueError):
            panel_2.add_entry(entry_2)
        # panel_1.remove_entry() should be successfully called
        self.assertFalse(entry_1.has_panel())
        self.assertEqual(panel_1.get_entries(), [])

        entry_2.date_time += timedelta(minutes=1)
        panel_2.add_entry(entry_2)

        self.assertEqual(panel_1.get_entries(), [])
        self.assertEqual(panel_2.get_entries(), [entry_2])
        panel_2.add_entry(entry_1)
        self.assertEqual(panel_2.get_entries(), [entry_2, entry_1])

    def test_metadata(self):
        # metadata validation (created, posted, filename, ...)
        pass
