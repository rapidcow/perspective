"""Test the psp.timeutil module."""
from datetime import datetime, timedelta
import unittest

from psp import timeutil


class TestParseTimezone(unittest.TestCase):
    """Test the function parse_timezone()."""

    def test_bad_offsets(self):
        """Test invalid offset strings."""
        bad_offsets = [
            '00:00.',
            '00:00.0',
            '00:00:00.1234567',
            '.1234',
            '08:00',
            'UTC08:00',
        ]
        for offset_str in bad_offsets:
            msg = f'invalid time zone string: {offset_str!r}'
            with self.assertRaisesRegex(ValueError, msg):
                timeutil.parse_timezone(offset_str)

    def test_good_offsets(self):
        offsets = [
            ('+08:00', timedelta(hours=8)),
            ('-07:00', timedelta(hours=-7)),
            ('+02:00:01', timedelta(hours=2, seconds=1)),
            ('-07:59:12.123', timedelta(hours=-7, minutes=-59, seconds=-12,
                                        microseconds=-123000)),
        ]
        sample_time = datetime(2020, 1, 1)
        for offset_str, offset in offsets:
            tz = timeutil.parse_timezone(offset_str)
            real_offset = sample_time.replace(tzinfo=tz).utcoffset()
            self.assertEqual(offset, real_offset)
