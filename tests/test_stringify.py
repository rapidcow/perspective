"""Test the psp.stringify module."""
from datetime import date, datetime, timedelta, timezone, tzinfo
from textwrap import dedent
import unittest

from psp import stringify
from psp.types import Entry, Panel


# XXX: Do we test wide characters now?

class TestStringifyPanel(unittest.TestCase):
    def test_basics(self):
        panel = Panel(date(2022, 1, 18))
        time = datetime(2022, 1, 18, 13, 0, 0, tzinfo=timezone.utc)
        entry = Entry(time)
        entry.set_data('Hello world!')
        panel.add_entry(entry)
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

    def test_entry_formatting(self):
        # Test if the time_format, time_zone, coerce_time_zone,
        # entry_indent options are passed on
        #
        # Test if the entry_formatter keyword argument works
        pass


class TestStringifyEntry(unittest.TestCase):
    def test_time_zone_coercion(self):
        panel = Panel(date(2021, 12, 25))
        pt = timezone(timedelta(hours=-8), 'PST')
        et = timezone(timedelta(hours=-5), 'EST')
        utc = timezone.utc
        entry = Entry(datetime(2021, 12, 25, 16, 40, tzinfo=utc))
        panel.add_entry(entry)
        entry.set_data('Text')
        formatter = stringify.EntryFormatter(width=33)

        formatter.configure(time_zone=pt)
        self.assertEqual(
            formatter.format(entry), dedent(
                """\
                4:40 PM [+00:00]
                  Text"""))
        formatter.configure(coerce_time_zone=True)
        # 4:40 PM UTC is equivalent to 8:40 AM in Pacific Standard Time
        self.assertEqual(
            formatter.format(entry), dedent(
                """\
                8:40 AM
                  Text"""))
        formatter.configure(time_zone=et)
        # This time it's 11:40 AM
        self.assertEqual(
            formatter.format(entry), dedent(
                """\
                11:40 AM
                  Text"""))

        # No coercion should take place if time zone matches
        formatter.configure(time_zone=utc)
        expected = dedent(
            """\
            4:40 PM
              Text""")
        self.assertEqual(formatter.format(entry), expected)
        formatter.configure(coerce_time_zone=False)
        self.assertEqual(formatter.format(entry), expected)

    # TODO: These
    def test_question(self):
        pass

    def test_caption(self):
        pass

    def test_transcription(self):
        pass

    def test_options(self):
        # Test these:
        # *  time format
        # *  label insight
        pass

    def test_horizontal_sep(self):
        # Test these:
        # *  date_time_sep
        # *  entry_title_attr_sep
        pass

    def test_vertical_sep(self):
        # Test these:
        # *  question_content_vsep
        # *  below_content_vsep
        pass
