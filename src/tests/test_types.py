"""Test the psp.types module."""
from random import randint
import datetime
import unittest

from psp.types import Entry, Panel


class TestPanel():
    def test_repr(self):
        pass

    def test_entries(self):
        tz = datetime.timezone(datetime.timedelta(hours=randint(-12, 12)))
        p = Panel(datetime.date(2021, 12, 17))
        e1 = Entry(p, datetime.datetime(2021, 12, 17, 13, 00, tzinfo=tz))
        e1.set_data('first entry')
        e2 = Entry(p, datetime.datetime(2021, 12, 17, 15, 20, tzinfo=tz))
        e2.set_data('second entry')
        entries = list(p.entries)
        self.assertEqual(entries, [e1, e2])


class TestEntry(unittest.TestCase):
    def test_repr(self):
        panel = Panel(datetime.date(2020, 2, 2))
        tz = datetime.timezone.utc
        the_time = datetime.datetime(2020, 2, 2, 14, 14, tzinfo=tz)
        entry = Entry(panel, the_time)
        self.assertEqual(repr(entry), f'<Entry object at {the_time}>')
        self.assertIn(entry, panel.get_entries())
        self.assertIs(entry.panel, panel)

    # def test_validation(self):
    #     today = datetime.date.today()
    #     panel = Panel(today)

    #     msg = 'date_time should be an aware datetime object'
    #     with self.assertRaisesRegex(TypeError, msg):
    #         Entry(panel, datetime.datetime(2020, 2, 2))

    #     tz = datetime.timezone(datetime.timedelta(hours=randint(-12, 12)))
    #     tm = datetime.time(0, 0, 0, tzinfo=tz)
    #     time = datetime.datetime.combine(today, tm)

    #     entry = Entry(panel, time)
    #     entry.data.update({'type': 'plain', 'encoding': 'ascii',
    #                        'raw': b'test'})
    #     # This shouldn't raise any exception
    #     entry.validate()
    #     self.assertIs(entry.date_time, time)

    #     entry.date_time -= datetime.timedelta(microseconds=1)
    #     msg = '^entry time .* earlier than start of day .*$'
    #     with self.assertRaisesRegex(ValueError, msg):
    #         entry.validate()

    #     entry.insight = True
    #     entry.date_time += datetime.timedelta(days=2)

    #     msg = '^entry is an insight and its time .* is less than 2 days .*$'
    #     with self.assertRaisesRegex(ValueError, msg):
    #         entry.validate()

    #     entry.date_time += datetime.timedelta(microseconds=1)
    #     # This shouldn't raise any exception either
    #     entry.validate()

    def test_metadata(self):
        # metadata validation (created, posted, filename, ...)
        pass
