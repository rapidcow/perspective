"""Test the psp.types module."""
from random import randint
from datetime import date, datetime, time, timedelta, timezone
import unittest

from psp.types import Entry, Panel


class TestEntry(unittest.TestCase):
    def test_repr(self):
        panel = Panel(date.today())
        tz = timezone.utc
        the_time = datetime(2020, 2, 2, 14, 14, tzinfo=tz)
        entry = Entry(panel, the_time)
        self.assertEqual(repr(entry), f'<Entry object at {the_time}>')

    def test_validation(self):
        today = date.today()
        panel = Panel(today)

        msg = 'date_time should be an aware datetime object'
        with self.assertRaisesRegex(TypeError, msg):
            Entry(panel, datetime(2020, 2, 2))

        tz = timezone(timedelta(hours=randint(-12, 12)))
        the_time = datetime.combine(today, time(0, 0, 0, tzinfo=tz))

        entry = Entry(panel, the_time)
        entry.data.update({'type': 'plain', 'encoding': 'ascii',
                           'data': b'test'})
        # This shouldn't raise any exception
        entry.validate()
        self.assertIs(entry.date_time, the_time)

        entry.date_time -= timedelta(microseconds=1)
        msg = '^entry time .* earlier than start of day .*$'
        with self.assertRaisesRegex(ValueError, msg):
            entry.validate()

        entry.insight = True
        entry.date_time += timedelta(days=2)

        msg = '^entry is an insight and its time .* is less than 2 days .*$'
        with self.assertRaisesRegex(ValueError, msg):
            entry.validate()

        entry.date_time += timedelta(microseconds=1)
        # This shouldn't raise any exception either
        entry.validate()
