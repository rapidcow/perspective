"""Test the psp.types module."""
from datetime import date, datetime, timezone, timedelta
import os
import tempfile
import unittest

from psp.types import Entry, Panel


class TestPanel(unittest.TestCase):
    def test_repr(self):
        panel_date = date(2021, 12, 25)
        panel = Panel(panel_date)
        self.assertEqual(repr(panel), f'<Panel object on {panel_date}>')

    def test_entry_protocol(self):
        panel = Panel(date(2021, 12, 17))

        tz = timezone(timedelta(hours=-8))
        entry1 = Entry(datetime(2021, 12, 17, 13, 0, tzinfo=tz))
        entry1.set_data('first entry')

        entry2 = Entry(datetime(2021, 12, 17, 15, 20, tzinfo=tz))
        entry2.set_data('second entry')
        panel.add_entry(entry1)
        panel.add_entry(entry2)

        self.assertEqual(panel.get_entries(), [entry1, entry2])
        self.assertIs(panel.get_entry(0), entry1)
        self.assertIs(panel.get_entry(1), entry2)
        self.assertIs(entry1.panel, panel)
        self.assertIs(entry2.panel, panel)

    def test_count(self):
        panel = Panel(date(2022, 2, 2))
        self.assertEqual(panel.count(), 0)
        for i in range(24):
            tz = timezone(timedelta(hours=-i))
            entry = Entry(datetime(2022, 2, 2, i, tzinfo=tz))
            panel.add_entry(entry)
        self.assertEqual(panel.count(), 24)

    def test_from_panel(self):
        panel = Panel(date(2022, 2, 22))
        tz = timezone.utc
        for i in range(12):
            entry = Entry(datetime(2022, 2, 22, i, tzinfo=tz))
            panel.add_entry(entry)
        panel_ii = Panel.from_panel(panel)
        self.assertEqual(panel_ii.date, panel.date)
        self.assertEqual(panel_ii.get_attributes(), panel.get_attributes())
        self.assertEqual(panel_ii.count(), 0)
        self.assertFalse(panel_ii.has_entries())


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
        msg = 'time should be an aware datetime object'
        with self.assertRaises(TypeError, msg=msg):
            Entry(datetime(2019, 8, 25, 10))

        entry_time = datetime(2019, 8, 24, 23, 59, 59, tzinfo=timezone.utc)
        entry = Entry(entry_time)
        msg = ('entry time ({}) earlier than start of day of the parent '
               'panel ({}) in local time').format(entry_time, panel_date)
        with self.assertRaises(ValueError, msg=msg):
            panel.add_entry(entry)
        entry.time += timedelta(minutes=1)
        panel.add_entry(entry)

        entry_time += timedelta(days=2)
        entry = Entry(entry_time, insight=True)
        msg = ('entry is an insight and its time ({}) is less than '
               '2 days apart from the start of day of the parent panel '
               '({}) in local time').format(entry_time, panel_date)
        with self.assertRaises(ValueError, msg=msg):
            panel.add_entry(entry)
        entry.time += timedelta(minutes=1)
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

        entry_1.time += timedelta(minutes=1)
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

        entry_2.time += timedelta(minutes=1)
        panel_2.add_entry(entry_2)

        self.assertEqual(panel_1.get_entries(), [])
        self.assertEqual(panel_2.get_entries(), [entry_2])
        panel_2.add_entry(entry_1)
        self.assertEqual(panel_2.get_entries(), [entry_2, entry_1])

    def test_raw_data_and_source(self):
        entry = Entry(datetime(2022, 6, 15, tzinfo=timezone.utc))
        self.assertEqual(entry.get_raw_data(), b'')
        self.assertIs(entry.get_source(), None)
        self.assertFalse(entry.has_source())

        fp = tempfile.NamedTemporaryFile(delete=False)
        try:
            with fp:
                fp.write(b'amogus')
            entry.set_source(fp.name)
            self.assertEqual(entry.get_raw_data(), b'amogus')
            self.assertTrue(entry.has_source())
            self.assertEqual(entry.get_source(), fp.name)
        finally:
            os.unlink(fp.name)

        entry.set_raw_data(b'hi')
        self.assertEqual(entry.get_raw_data(), b'hi')
        self.assertFalse(entry.has_source())
        self.assertIs(entry.get_source(), None)

        with self.assertRaises(TypeError):
            entry.set_raw_data(None)
        with self.assertRaises(TypeError):
            entry.set_source(None)

    def test_equality(self):
        e1 = Entry(datetime(2022, 6, 18, 10, 40, tzinfo=timezone.utc))
        e2 = Entry(datetime(2022, 6, 18, 10, 40, tzinfo=timezone.utc))
        e1.set_data('na\u00efve', encoding='utf-8')
        e2.set_data('na\u00efve', encoding='latin')
        self.assertTrue(e1.is_text())
        self.assertTrue(e2.is_text())
        self.assertEqual(e1, e2)
        e1.set_encoding('binary')
        e2.set_encoding('binary')
        self.assertFalse(e1.is_text())
        self.assertFalse(e2.is_text())
        self.assertNotEqual(e1, e2)

    def test_from_entry(self):
        entry = Entry(datetime(2022, 2, 2, 9, tzinfo=timezone.utc))
        entry.insight = True
        entry.set_data('i set insight to True for no reason and '
                       'i hate myself')
        entry_ii = Entry.from_entry(entry)
        self.assertEqual(entry, entry_ii)
        self.assertEqual(entry.get_raw_data(), entry_ii.get_raw_data())
        self.assertEqual(entry.get_source(), entry_ii.get_source())
        self.assertEqual(entry.get_encoding(), entry_ii.get_encoding())
