"""Test the psp.timeutil module."""
import datetime
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
        ]
        for offset_str in bad_offsets:
            msg = f'invalid time zone: {offset_str!r}'
            with self.assertRaisesRegex(ValueError, msg):
                timeutil.parse_timezone(offset_str)
