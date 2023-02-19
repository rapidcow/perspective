"""Test the psp.processors.json_processor module."""
import base64
import collections
from datetime import date, datetime, timezone
import functools
import json
import os, pathlib
import shutil
import string
from textwrap import dedent
import types
import unittest
import unittest.mock

from . import *
from psp.types import Entry, Panel
from psp.processors.json_processor import (
    JSONLoader, LoadError, LoadWarning,
    JSONDumper, DumpError, DumpWarning, InferenceManager,
    load_json, dump_json,
    # find_paths, get_lookup_paths,
)


class TestJSONLoader(unittest.TestCase):
    """Test the JSONLoader class."""
    @tempdir
    def _test_type(self, root, factory, attr_type, msg_factory,
                   allow_none=False):
        """Test whether TypeError is thrown when a certain JSON field
        takes on different types.

        factory : function that takes one argument (the field's value in
                  JSON) and returns JSON file content
        attr_type : Python class of the only valid type
        msg_factory : function that takes one argument (the parsed value
                      from JSON) and returns the error message
        allow_none : whether None is considered valid
        """
        with open_with_unicode(root / 'backup.json', 'x+') as fp:
            for (json_value, py_value) in [
                    ('"sus"', 'sus'),   # string
                    ('null', None),     # null
                    ('true', True),     # boolean
                    ('false', False),
                    ('[]', []),         # array
                    ('{}', {}),         # object
                    ('0', 0),           # int
                    ('1.0', 1.0),       # float
                ]:
                # can't use isinstance here bcuz bool is a subclass of int
                # (and so like isinstance(True, int) would actually be true)
                if type(py_value) is attr_type:
                    continue
                if py_value is None and allow_none:
                    continue
                fp.write(factory(json_value))
                fp.seek(0)
                with self.assertRaisesRegex(TypeError, msg_factory(py_value)):
                    collections.deque(JSONLoader().load(fp), maxlen=0)
                fp.seek(0)
                fp.truncate(0)

    @tempdir
    def _test_method_hook(self, root, factory, getter, cls, name, values,
                            *args, **kwargs):
        """Test if a certain method is called to parse a certain value.

        factory : function that takes a value from 'values' and returns
                  the JSON file content
        getter : function that takes (loader, fp) and return the
                 parsed value
        cls : the class to be tested
        name : name of the method that parses the value
        values : values to test
        *args, **kwargs : extra arguments to pass to the method
                          to parse the value; should be the same
                          arguments as those of the latest call
        """
        with open_with_unicode(root / 'backup.json', 'x+') as fp:
            for json_value in values:
                fp.write(factory(json_value))
                fp.seek(0)
                method = getattr(cls(), name)
                with unittest.mock.patch.object(
                        cls, name, side_effect=method) as mock_method:
                    # instance needs to be recreated after
                    # mock method is inserted
                    loader = cls()
                    got = getter(loader, fp)
                    mock_method.assert_called_with(
                        json_value, *args, **kwargs)
                    expected = method(json_value, *args, **kwargs)
                self.assertEqual(got, expected)
                fp.seek(0)
                fp.truncate(0)

    # TEST 1
    # ------
    @tempdir
    def test_date(self, root):
        """Test the `date` key at panel level."""
        # 1. When not provided, ERROR ("panel must provide date")
        file = root / 'backup.json'
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "data": [
                    {}
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = 'panel must provide date'
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        # 2. Must be a str
        template = string.Template(dedent("""\
            {
              "data": [
                {
                  "date": $date
                }
              ]
            }
            """))
        self._test_type(lambda s: template.substitute(date=s), str,
                          lambda v: ("'date': expected a str, got {}"
                                     .format(type(v).__name__)))

        # 3. Valid to self.parse_date()
        def json_factory(date_str):
            return template.substitute(date=json.dumps(date_str))

        def date_getter(loader, fp):
            # I'm using iterable unpacking since it ensures
            # we're not getting an arbitrary length of objects
            (panel,) = loader.load(fp)
            return panel.date

        good_dates = ['2018-09-04', '2022-02-02']
        self._test_method_hook(json_factory, date_getter, JSONLoader,
                                 'parse_date', good_dates)

        # XXX: I just realized that parse_date() still works when it
        # returns a datetime.datetime instance (if I droppped the .date()
        # that is) since datetime is a subclass of date.  Should we allow
        # this to be the case? since literally this means datetime can
        # act as a date like the first argument to datetime.combine()...
        class CustomLoader(JSONLoader):
            __slots__ = ()
            def parse_date(self, s):
                try:
                    return datetime.strptime(s, '%b %d %Y').date()
                except ValueError:
                    pass
                return super().parse_date(s)

        good_dates.extend(['Nov 18 2011', 'Nov  4 2014'])
        loader = CustomLoader()
        self._test_method_hook(json_factory, date_getter, CustomLoader,
                                 'parse_date', good_dates)

    # TEST 2
    # ------
    @tempdir
    def test_time(self, root):
        """Test the `time` and `date-time` keys at entry level.
        The optional `date` key when `time` is provided too.
        """
        file = root / 'backup.json'
        # 1. If neither provided, ERROR ("entry must provide time ...")
        with open_with_unicode(file, 'x') as fp:
            fp.write(dedent("""\
                {
                  "tz": "UTC",
                  "data": [
                    {
                      "date": "2022-02-02",
                      "entries": [
                        {
                          "data": "no time or date-time"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = ("entry must provide time, either through the key "
                   "'time' or 'date-time'")
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        # 2. Both provided, ERROR ("exactly one ... can be provided")
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "tz": "UTC",
                  "data": [
                    {
                      "date": "2022-02-02",
                      "entries": [
                        {
                          "time": "14:22",
                          "date-time": "2022-02-02 14:22",
                          "data": "both time and date-time"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = "exactly one of 'date-time' and 'time' can be provided"
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "tz": "UTC",
                  "data": [
                    {
                      "date": "2022-02-02",
                      "entries": [
                        {
                          "date": "2022-03-03",
                          "time": "14:22",
                          "date-time": "2022-02-02 14:22",
                          "data": "both time (with date) and date-time"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = "exactly one of 'date-time' and 'time' can be provided"
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        # 3. date applies locally
        # 4. date-time overrides everything
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "tz": "UTC",
                  "data": [
                    {
                      "date": "2022-02-02",
                      "entries": [
                        {
                          "date": "2022-02-22",
                          "time": "14:22",
                          "data": "overridden"
                        },
                        {
                          "time": "14:23",
                          "data": "reverted"
                        },
                        {
                          "date-time": "2022-03-14 15:29",
                          "data": "overridden again"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            (panel,) = JSONLoader(check_entry_order=False).load(fp)
        (entry1, entry2, entry3) = panel.entries()
        self.assertEqual(entry1.time.timetuple()[:6],
                         (2022, 2, 22, 14, 22, 0))
        self.assertEqual(entry2.time.timetuple()[:6],
                         (2022, 2, 2, 14, 23, 0))
        self.assertEqual(entry3.time.timetuple()[:6],
                         (2022, 3, 14, 15, 29, 0))

        # 5. When date-time and date are provided, date is ignored
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "tz": "UTC",
                  "data": [
                    {
                      "date": "2022-02-02",
                      "entries": [
                        {
                          "date": "2022-04-18",
                          "date-time": "2022-06-28 03:18",
                          "data": "date won't have an effect"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = "ignored entry key: date"
            with self.assertWarnsRegex(LoadWarning, msg):
                next(JSONLoader().load(fp))

        # 6. All attributes must be a str
        template = string.Template(dedent("""\
            {
              "data": [
                {
                  "date": "2021-12-17",
                  "entries": [
                    {
                      $extra
                      "$name": $value
                    }
                  ]
                }
              ]
            }
            """))
        msg = '{!r}: expected a str, got {}'
        for name in 'time', 'date-time', 'date':
            # The 'date' variable won't be seen unless 'time' is provided
            e = '"time": "10:00+08:00",' if name == 'date' else ''
            self._test_type(
                lambda s: template.substitute(extra=e, name=name, value=s),
                str, lambda v: msg.format(name, type(v).__name__))

        # 7. time -> self.parse_time()
        #    date-time -> self.parse_datetime()
        #    date -> self.parse_date()
        template = string.Template(dedent("""\
            {
              $tlextra
              "data": [
                {
                  "date": "2018-09-01",
                  "entries": [
                    {
                      $extra
                      "$name": "$value",
                      "data": "sample data"
                    }
                  ]
                }
              ]
            }
            """))

        def date_getter(loader, fp):
            (panel,) = loader.load(fp)
            return panel.get_entry(0).time.date()

        def time_getter(loader, fp):
            (panel,) = loader.load(fp)
            return panel.get_entry(0).time.timetz()

        def date_time_getter(loader, fp):
            (panel,) = loader.load(fp)
            return panel.get_entry(0).time

        def make_time_parser(loader, tz):
            return functools.partial(loader.parse_time,
                                     tzinfo=tz, fold=None)

        def make_date_time_parser(loader, tz):
            return functools.partial(loader.parse_datetime,
                                     tzinfo=tz, fold=None)

        ##########
        # Time   #
        ##########
        good_naive_time = ['10:00', '12:00', '22:00']
        good_aware_time = ['06:00+08:00', '19:00-07:00']

        loader = JSONLoader()
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='"tz": "UTC",', extra='', name='time', value=s),
            time_getter,
            JSONLoader,
            'parse_time',
            good_naive_time + good_aware_time,
            tzinfo=JSONLoader().parse_timezone('UTC'),
            fold=None)

        # tests exclusive to aware time
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='', name='time', value=s),
            time_getter,
            JSONLoader,
            'parse_time',
            good_aware_time,
            tzinfo=None,
            fold=None)

        class CustomTimeLoader(JSONLoader):
            __slots__ = ()
            def parse_time(self, s, *, tzinfo, fold):
                for time_format in ('%I:%M %p', '%I:%M%z %p'):
                    try:
                        base = datetime.strptime(s, time_format)
                    except ValueError:
                        pass
                    else:
                        # usually user implementation should do an
                        # appropriate substitution with the given tzinfo
                        # and fold, but here's i'm just gonna be lazy :I
                        d = {}
                        JSONDumper().write_entry_time(d, base)
                        s = d['time']
                        break
                return super().parse_time(s, tzinfo, fold)

        good_naive_time.extend(['08:00 AM', '04:00 PM'])
        good_aware_time.extend(['07:00-07:00 PM', '03:00+08:00 AM'])
        loader = CustomTimeLoader()
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='"tz": "UTC",', extra='', name='time', value=s),
            time_getter,
            CustomTimeLoader,
            'parse_time',
            good_naive_time + good_aware_time,
            tzinfo=JSONLoader().parse_timezone('UTC'),
            fold=None)

        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='', name='time', value=s),
            time_getter,
            CustomTimeLoader,
            'parse_time',
            good_aware_time,
            tzinfo=None,
            fold=None)

        ###############
        # Date time   #
        ###############
        good_naive_datetime = ['2022-02-22 22:22', '2021-08-30 10:10']
        good_aware_datetime = ['2022-02-22 14:22+02:00',
                               '2021-09-15 19:00+08:00']

        loader = JSONLoader()
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='"tz": "UTC",', extra='', name='date-time', value=s),
            date_time_getter,
            JSONLoader,
            'parse_datetime',
            good_naive_datetime + good_aware_datetime,
            tzinfo=JSONLoader().parse_timezone('UTC'),
            fold=None)

        # tests exclusive to aware date time
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='', name='date-time', value=s),
            date_time_getter,
            JSONLoader,
            'parse_datetime',
            good_aware_datetime,
            tzinfo=None,
            fold=None)

        class CustomDateTimeLoader(JSONLoader):
            __slots__ = ()
            def parse_datetime(self, s, *, tzinfo, fold):
                for dt_format in ('%b %d %H:%M %Y', '%b %d %H:%M%z %Y'):
                    try:
                        base = datetime.strptime(s, dt_format)
                    except ValueError:
                        pass
                    else:
                        d = {}
                        JSONDumper().write_entry_date_and_time(d, base)
                        s = d['date-time']
                        break
                return super().parse_datetime(s, tzinfo=tzinfo, fold=fold)

        good_naive_datetime.extend(['Dec 16 17:00 2021', 'Jul 25 05:40 2022'])
        good_aware_datetime.extend(['Feb 02 02:22+02:22 2022',
                                    'Sep 15 19:00+08:00 2021'])

        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='"tz": "UTC",', extra='', name='date-time', value=s),
            date_time_getter,
            CustomDateTimeLoader,
            'parse_datetime',
            good_naive_datetime + good_aware_datetime,
            tzinfo=JSONLoader().parse_timezone('UTC'),
            fold=None)

        # tests exclusive to aware date time
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='', name='date-time', value=s),
            date_time_getter,
            CustomDateTimeLoader,
            'parse_datetime',
            good_aware_datetime,
            tzinfo=None,
            fold=None)

        #################
        # Date (entry)  #
        #################
        good_dates = ['2018-09-04', '2022-02-02']
        loader = JSONLoader()
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='"time": "08:00+08:00",', name='date',
                value=s),
            date_getter,
            JSONLoader,
            'parse_date',
            good_dates)

        class CustomDateLoader(JSONLoader):
            __slots__ = ()
            def parse_date(self, s):
                try:
                    return datetime.strptime(s, '%b %d %Y').date()
                except ValueError:
                    pass
                return super().parse_date(s)

        good_dates.extend(['Nov 18 2021', 'Dec 25 2021'])
        loader = CustomDateLoader()
        self._test_method_hook(
            lambda s: template.substitute(
                tlextra='', extra='"time": "08:00+08:00",', name='date',
                value=s),
            date_getter,
            CustomDateLoader,
            'parse_date',
            good_dates)

    # TEST 3
    # ------
    @tempdir
    def test_data_and_input(self, root):
        """Test the `data` and `input` keys at entry level and the most
        basic cases for inference.
        """
        file = root / 'backup.json'
        # 1. When neither is provided, ERROR ("at least one should be
        #    specified")
        with open_with_unicode(file, 'x') as fp:
            fp.write(dedent("""\
                {
                  "data": [
                    {
                      "date": "2022-07-30",
                      "entries": [
                        {
                          "time": "22:30+08:00"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = "at least one of 'data' and 'input' should be specified"
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        # 2. When both are provided, ERROR ("only one ... can be specified")
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "data": [
                    {
                      "date": "2022-02-22",
                      "entries": [
                        {
                          "time": "14:22+00:00",
                          "data": "twosday",
                          "input": "twosday.txt"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            msg = "only one of 'data' and 'input' can be specified"
            with self.assertRaisesRegex(LoadError, msg):
                next(JSONLoader().load(fp))

        # 3. Inline text -> enc = utf-8
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "data": [
                    {
                      "date": "2022-02-22",
                      "entries": [
                        {
                          "time": "14:22+00:00",
                          "data": "twosday"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(file) as fp:
            (panel,) = JSONLoader().load(fp)
            (entry,) = panel.entries()
            self.assertEqual(entry.get_data(), 'twosday')
            self.assertEqual(entry.get_type(), 'plain')
            self.assertEqual(entry.get_encoding(), 'utf-8')

        # 4. External file -> enc = type = binary
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent("""\
                {
                  "data": [
                    {
                      "date": "2022-02-22",
                      "entries": [
                        {
                          "time": "14:22+00:00",
                          "input": "ice-cube"
                        }
                      ]
                    }
                  ]
                }
                """))
        with open_with_unicode(root / 'ice-cube', 'x') as fp:
            fp.write('TEAM ICE CUBE!')
        with open_with_unicode(file) as fp:
            (panel,) = JSONLoader(base_dir=root).load(fp)
            (entry,) = panel.entries()
            self.assertEqual(entry.get_data(),
                             'TEAM ICE CUBE!'.encode('utf-8'))
            self.assertEqual(entry.get_type(), 'binary')
            self.assertEqual(entry.get_encoding(), 'binary')

        # 5. Inline binary -> enc = type = binary
        with open_with_unicode(file, 'w') as fp:
            fp.write(dedent(string.Template("""\
                {
                  "data": [
                    {
                      "date": "2022-02-22",
                      "entries": [
                        {
                          "time": "14:22+00:00",
                          "data": "$s",
                          "data-encoding": "base64"
                        }
                      ]
                    }
                  ]
                }
                """).substitute(s=(base64.b64encode(b'twosday')
                                   .decode('ascii')))))
        with open_with_unicode(file) as fp:
            (panel,) = JSONLoader().load(fp)
            (entry,) = panel.entries()
            self.assertEqual(entry.get_data(), b'twosday')
            self.assertEqual(entry.get_type(), 'binary')
            self.assertEqual(entry.get_encoding(), 'binary')


class TestJSONDumper(unittest.TestCase):
    """Test the JSONDumper class."""

    # TEST 1
    # ------
    def test_top_level_attributes(self):
        """Test get_top_level_attributes() and prepare_backup()."""
        for tz in make_tz(hours=8), make_tz(), None:
            for paths in ['assets'], [], ['.']:
                dumper = JSONDumper(time_zone=tz, paths=paths)
                attrs = dumper.get_top_level_attributes([])
                json_attrs = {}
                dumper.prepare_backup(json_attrs, attrs)

                # top-level attributes
                self.assertIs(attrs['tz'], tz)
                self.assertEqual(attrs['paths'], paths)

                # JSON top-level attributes
                if paths == ['.']:
                    self.assertNotIn('paths', json_attrs)
                else:
                    self.assertEqual(json_attrs['paths'], paths)
                if tz is None:
                    self.assertNotIn('tz', json_attrs)
                else:
                    tzstr = dumper.format_timezone(tz)
                    self.assertEqual(json_attrs['tz'], tzstr)

    @tempdir
    def test_generate_export_path(self, root):
        """Test generate_export_path() and related methods"""
        utc = timezone.utc
        # Test this dir structure
        #
        #   a/1.txt
        #   b/1.txt
        #

        # Matching file content and path
        entry_a = Entry(datetime(2022, 2, 22, 14, 30, tzinfo=utc))
        entry_a.set_data('sample text', type='type_a')

        class TestDumper(JSONDumper):
            def get_input_path(self, entry, attrs):
                paths = attrs['paths']
                if entry.get_type() == 'type_a':
                    dirname, base, ext = 'a', '1', '.txt'
                elif entry.get_type() == 'type_b':
                    dirname, base, ext = 'b', '1', '.txt'
                filename = self.generate_export_path(entry, base, ext,
                                                     dirname, paths)
                self.export_entry(entry, os.path.join(dirname, filename))
                return self.compute_input_path(filename, dirname, paths)

        dumper = TestDumper(base_dir=root, paths=['a', 'b'])
        attrs = dumper.get_top_level_attributes([])
        for _ in range(2):
            self.assertEqual(dumper.wrap_entry(entry_a, attrs), {
                    'date-time': '2022-02-22 14:30+00:00',
                    'type': 'type_a', 'encoding': 'utf-8',
                    'input': '1.txt',
                })
        with open_with_unicode(root / 'a' / '1.txt') as fp:
            self.assertEqual(fp.read(), 'sample text')
        shutil.rmtree(root / 'a')

        # Matching file content and un-matching path
        entry_b = entry_a.copy()
        entry_b.set_type('type_b')

        self.assertEqual(dumper.wrap_entry(entry_a, attrs), {
                'date-time': '2022-02-22 14:30+00:00',
                'type': 'type_a', 'encoding': 'utf-8',
                'input': '1.txt',
            })
        with open_with_unicode(root / 'a' / '1.txt') as fp:
            self.assertEqual(fp.read(), 'sample text')

        self.assertEqual(dumper.wrap_entry(entry_b, attrs), {
                'date-time': '2022-02-22 14:30+00:00',
                'type': 'type_b', 'encoding': 'utf-8',
                'input': '1_001.txt',
            })
        with open_with_unicode(root / 'b' / '1_001.txt') as fp:
            self.assertEqual(fp.read(), 'sample text')


class TestInferenceManager(unittest.TestCase):
    """Test the InferenceManager class."""
