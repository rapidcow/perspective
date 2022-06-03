"""Test the psp.stringify module."""
from datetime import date, datetime, timedelta, timezone, tzinfo
from textwrap import dedent
import unittest

from psp import stringify
from psp.types import Entry, Panel


# XXX: Do we test wide characters now?

class FormatterSubclass(stringify.Formatter):
    # Concrete implementation which we aren't really using
    def format(self, obj):
        return str(obj)

    # Expose protected methods
    def wrap_paragraph(self, *args, **kwargs):
        return self._wrap_paragraph(*args, **kwargs)

    def center_paragraph(self, *args, **kwargs):
        return self._center_paragraph(*args, **kwargs)


ZERO = timedelta(0)
HOUR = timedelta(hours=1)


class TzWithFold(tzinfo):
    """An imaginary time zone where the offset is -7 before Nov 07 2021 02:00
    in local time but falls back to -8 from that time and on.

    This mimics the falling back from Pacific Daylight Time to
    Pacific Standard Time.

    As per PEP 495, the FOLD attribute is used to disambiguate the time
    period from Nov 07 2021 01:00 (inclusive) to 02:00 (exclusive) in local
    time where a value of 1 denotes the offset after the change (-8) and 0
    denotes the offset before the change (-7).

    UTC to local time:

            UTC | 08:00 | 08:30 | 08:59 | 09:00 | 09:30 | 09:59 | 10:00
        --------+-------+-------+-------+-------+-------+-------+-------
         -07:00 | 01:00 | 01:30 | 01:59 |       |       |       |
         -08:00 |       |       |       | 01:00 | 01:30 | 01:59 | 02:00
                 ^~~~~~~~~~~~~~~~~~~~~^   ^~~~~~~~~~~~~~~~~~~~^
                        fold = 0                fold = 1

    Local time to UTC:

             00:00 | 00:30 |     01:00 | 01:30 | 01:59 |     02:00 | 02:30
        -----------+-------+-----------+-------+-------+-----------+-------
         (U) 07:00 | 07:30 | (0) 08:00 | 08:30 | 08:59 |           |
                   |       | (1) 09:00 | 09:30 | 09:59 | (U) 10:00 | 10:11

    (U) stands for unaffected (the fold attribute is ignored); (0) and (1)
    denote fold being 0 and 1 respectively.
    """
    # Date of time zone change in local time, at 2 AM
    MOVE_TIME = datetime(2021, 11, 7, 2)

    def utcoffset(self, dt):
        # dt.astimezone() subtracts this from the time, so it's
        # kind of like adding 7 or 8 hours to the local time to get
        # the UTC time...
        dt = dt.replace(tzinfo=None)
        if dt < self.MOVE_TIME - HOUR:
            return -7 * HOUR
        # Ambiguous local time where [MOVE_TIME - HOUR, MOVE_TIME) occurs
        # twice
        if self.MOVE_TIME - HOUR <= dt < self.MOVE_TIME:
            return -8 * HOUR if dt.fold else -7 * HOUR
        return -8 * HOUR

    def fromutc(self, dt):
        # The input to this function is a datetime with UTC values
        # but with a tzinfo set to self.
        if not isinstance(dt, datetime):
            raise TypeError('fromutc() requires a datetime argument')
        if dt.tzinfo is not self:
            raise ValueError('dt.tzinfo is not self')

        # To make it consistent let's convert the UTC time to local time
        # with an offset of -7 (before the change) assumed.
        # Take it as a naive guess before making adjustments or something idk
        dt = dt.replace(tzinfo=None) - 7*HOUR
        # The current time is fine as long as it's before falling back
        if dt < self.MOVE_TIME:
            return dt.replace(tzinfo=self)
        # Within an hour after falling back, we're repeating the same
        # interval so fold needs to be set to 1
        if self.MOVE_TIME <= dt < self.MOVE_TIME + HOUR:
            return (dt - HOUR).replace(tzinfo=self, fold=1)
        return (dt - HOUR).replace(tzinfo=self)

    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        if dt >= self.MOVE_TIME:
            return '-08:00'
        return '-07:00'

    def __repr__(self):
        return f'{type(self).__name__}()'

    def __str__(self):
        return f'{type(self).__name__}'


class TestFormatter(unittest.TestCase):
    def test_wrap_paragraph(self):
        f = FormatterSubclass(width=10)
        # Empty strings should result in an empty list only if
        # return_empty is True
        self.assertEqual(f.wrap_paragraph(''), [''])
        self.assertEqual(f.wrap_paragraph('', prefix='. '), ['.'])
        self.assertEqual(f.wrap_paragraph('', return_empty=True), [])
        self.assertEqual(f.wrap_paragraph('', prefix='. ', return_empty=True),
                         [])
        # Inputting string containing merely whitespace characters
        # should give nothing but the prefix
        self.assertEqual(f.wrap_paragraph(' \t\n'), [''])
        self.assertEqual(f.wrap_paragraph('hello world'), ['hello', 'world'])
        self.assertEqual(f.wrap_paragraph('hi world'), ['hi world'])
        self.assertEqual(f.wrap_paragraph('hello world', prefix='> '),
                         ['> hello', '  world'])

        # Indentation
        # -----------
        f.set_indent('| ')
        self.assertEqual(f.wrap_paragraph(''), ['|'])
        self.assertEqual(f.wrap_paragraph(' \t\n'), ['|'])
        self.assertEqual(f.wrap_paragraph('hello world'),
                         ['| hello', '| world'])
        self.assertEqual(f.wrap_paragraph('hello world', prefix='> '),
                         ['| > hello', '|   world'])

        # Disabled wrapping
        # -----------------
        f.width = None
        self.assertEqual(f.wrap_paragraph('hello world'), ['| hello world'])
        f.width = 8
        f.wrapper = None
        self.assertEqual(f.wrap_paragraph('hello world'), ['| hello world'])
        f.set_indent('ps> ')
        self.assertEqual(f.wrap_paragraph('hello world'),
                         ['ps> hello world'])

    def test_center_paragraph(self):
        # The extra character should be added to the RIGHT instead of
        # to the LEFT.
        f = FormatterSubclass(width=10)
        self.assertEqual(f.center_paragraph(''), [''])
        self.assertEqual(f.center_paragraph('hi world'),
                         [' hi world '.rstrip()])
        self.assertEqual(
            f.center_paragraph('hello world!'),
            ['  hello   '.rstrip(),
             '  world!  '.rstrip()])

        # Indentation
        # -----------
        f.set_indent('|')
        self.assertEqual(f.center_paragraph(''), ['|'])
        self.assertEqual(f.center_paragraph('hi'), ['|   hi    '.rstrip()])
        f.configure(line_callback=lambda s: s)
        self.assertEqual(f.center_paragraph('hi'), ['|   hi    '])
        self.assertEqual(
            f.center_paragraph('hello world'),
            ['|  hello  ',
             '|  world  '])


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

    def test_options(self):
        # Test these
        # *  entry indent
        # *  base directory
        #
        # make sure the order of entries in a panel is preserved!
        pass


class TestStringifyEntry(unittest.TestCase):
    def test_content(self):
        # test the edge case of get_content() returning ''
        pass

    def test_time_zone_fold(self):
        entries = []
        panel = Panel(date(2021, 11, 7))
        dt = datetime(2021, 11, 7, 7, 30, tzinfo=timezone.utc)
        for mm in range(0, 180, 30):
            # Make it so that tz = -3, -2, -1, 0, 1, 2
            tz = timezone(timedelta(hours=-3 + mm//30))
            entry = Entry((dt + timedelta(minutes=mm)).astimezone(tz))
            entry.set_data('Text')
            panel.add_entry(entry)
            entries.append(entry)
        entry = Entry(datetime(2021, 11, 7, 9, 30, tzinfo=timezone.utc)
                      .astimezone(TzWithFold()))
        entry.set_data('Text')
        panel.add_entry(entry)
        entries.append(entry)
        formatter = stringify.EntryFormatter()
        formatter.configure(time_zone=TzWithFold(), coerce_time_zone=True)
        fmt = '{}\n  Text'.format
        expected = map(
            fmt,
            ('12:30 AM', '1:00 AM', '1:30 AM',
             '1:00 AM [fold = 1]', '1:30 AM [fold = 1]',
             '2:00 AM', '1:30 AM [fold = 1]'))
        for exp, entry in zip(expected, entries):
            self.assertEqual(formatter.format(entry), exp)
        formatter.configure(coerce_time_zone=False)
        expected = map(
            fmt,
            ('4:30 AM [-03:00]', '6:00 AM [-02:00]', '7:30 AM [-01:00]',
             '9:00 AM [+00:00]', '10:30 AM [+01:00]', '12:00 PM [+02:00]',
             '1:30 AM [fold = 1]'))
        for exp, entry in zip(expected, entries):
            self.assertEqual(formatter.format(entry), exp)

        entries.clear()
        # cleaning after ourselves even though this isn't really needed
        while panel.has_entries():
            panel.pop_entry()
        dt = datetime(2021, 11, 7, 7, 30, tzinfo=timezone.utc)
        for mm in range(0, 180, 30):
            entry = Entry((dt + timedelta(minutes=mm))
                          .astimezone(TzWithFold()))
            entry.set_data('Text')
            panel.add_entry(entry)
            entries.append(entry)
        expected = map(
            fmt,
            ('12:30 AM', '1:00 AM', '1:30 AM',
             '1:00 AM [fold = 1]', '1:30 AM [fold = 1]',
             '2:00 AM'))
        # Should look the same regardless of time coercion
        for value in True, False:
            formatter.configure(coerce_time_zone=value)
            for exp, entry in zip(expected, entries):
                self.assertEqual(formatter.format(entry), exp)
        formatter.configure(time_zone=timezone.utc)
        expected = map(
            fmt,
            ('12:30 AM [-07:00]', '1:00 AM [-07:00]', '1:30 AM [-07:00]',
             '1:00 AM [-08:00]', '1:30 AM [-08:00]', '2:00 AM [-08:00]'))
        for exp, entry in zip(expected, entries):
            self.assertEqual(formatter.format(entry), exp)

    def test_time_zone_coercion(self):
        pst = timezone(timedelta(hours=-8), 'PST')
        est = timezone(timedelta(hours=-5), 'EST')
        some_tz = timezone(timedelta(hours=1))
        entry = Entry(datetime(2021, 12, 25, 16, 40, tzinfo=some_tz))
        Panel(date(2021, 12, 25)).add_entry(entry)
        entry.set_data('Text')
        formatter = stringify.EntryFormatter()

        fmt = '{}\n  Text'.format
        formatter.configure(time_zone=pst)
        self.assertEqual(formatter.format(entry), fmt('4:40 PM [+01:00]'))
        formatter.configure(coerce_time_zone=True)
        # 3:40 PM UTC is equivalent to 7:40 AM in Pacific Standard Time
        self.assertEqual(formatter.format(entry), fmt('7:40 AM'))
        formatter.configure(time_zone=est)
        # This time it should be 10:40 AM
        self.assertEqual(formatter.format(entry), fmt('10:40 AM'))

        # No coercion should take place if time zone matches
        formatter.configure(time_zone=timezone(timedelta(hours=1)))
        self.assertEqual(formatter.format(entry), fmt('4:40 PM'))
        formatter.configure(coerce_time_zone=False)
        self.assertEqual(formatter.format(entry), fmt('4:40 PM'))

    def test_infer_time_zone(self):
        pass

    def test_title(self):
        # Long title, short title and stuff
        pass

    # TODO: These
    def test_entry_title(self):
        pass

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
        # *  base directory
        pass

    def test_horizontal_sep(self):
        # Test these:
        # *  date_time_sep
        # *  entry_title_attr_sep
        pass

    def test_vertical_sep(self):
        # Test these:
        # *  title_entries_vsep
        # *  question_content_vsep
        # *  below_content_vsep
        #
        # MAKE SURE THAT ALL VSEP WORK (including those from
        # PanelFormatter) WHEN NON-WHITESPACE INDENT IS SET
        pass


class TestFormatSize(unittest.TestCase):
    def test_a_bunch_of_random_cases(self):
        for unit in ('tens', 'twos'):
            self.t('0 B', 0, unit=unit)
            self.t('0xB', 0, unit=unit, sep='x')
            self.t('17 B', 17, unit=unit)
            self.t('999 B', 999, unit=unit)
        self.t('1023 B', 1023, unit='twos')
        self.t('1.02 kB', 1023)
        self.t('1 kB', 1000, unit='tens')
        self.t('1.01 kB', 1006, unit='tens')
        self.t('1 KiB', 1024, unit='twos')
        self.t('1.12 GB', 1119106721)
        self.t('1.04 GiB', 1119106721, unit='twos')
        self.t('35.9MB', 35898538, sep='')
        self.t('359.0 MB', 358985380)
        # just to be certain that this function only knows English
        msg = "unit must be either 'tens' or 'twos'"
        for unit in ('deux', 'diez', '\u4e8c', 'ten', 'two'):
            with self.assertRaises(ValueError, msg=msg):
                stringify.format_size(123456, unit=unit)
            with self.assertRaises(ValueError, msg=msg):
                stringify.format_size(123456, unit=unit)

    def t(self, name, *args, **kwargs):
        self.assertEqual(stringify.format_size(*args, **kwargs), name)
