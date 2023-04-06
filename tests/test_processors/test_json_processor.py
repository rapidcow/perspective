"""Test the psp.serializers.json module."""
import copy
from datetime import date, time, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import psp.filetypes as filetypes
import psp.serializers.json as processor
from psp.types import Panel, Entry


def setUpModule():
    global TDIR, ROOT
    TDIR = tempfile.TemporaryDirectory()
    ROOT = Path(TDIR.name)


def tearDownModule():
    TDIR.cleanup()


def open(*args, **kwargs):
    if 'encoding' in kwargs:
        raise ValueError("encoding should not be passed "
                         "(will be overridden with 'utf-8')")
    kwargs['encoding'] = 'utf-8'
    return io.open(*args, **kwargs)


# Convenience methods for creating JSON backup files
def make_backup(panels, tz='UTC'):
    """Make a basic backup 'dict' from the list of dates of panels.

    This will look something like this:

        {
            "tz": tz,
            "data": [
                { "date": panels[0] },
                { "date": panels[1] },
                { "date": panels[2] },
                ...
            ]
        }
    """
    obj = {'tz': tz}
    if panels:
        panel_list = obj['data'] = []
        for date_obj in panels:
            panel_list.append({'date': str(date_obj)})
    return obj


def add_entries(obj, entries):
    """Add a list of list of entry dictionaries 'entries' to 'obj'.
    The key 'entries' is automatically created and assigned an empty list
    if it does not exist, after which each entry is appended to it.
    """
    for panel, ents in zip(obj['data'], entries):
        entry_list = panel.setdefault('entries', [])
        for entry in ents:
            entry_list.append(entry)


# JSONDumper.dump_data() always creates the archive with
# the 'data' field, so it's safe to just pop it.
def split_data(data):
    panels = data.pop('data')
    return panels, data


# I/O
def write_json(file, obj):
    with open(file, 'w') as fp:
        json.dump(obj, fp)


def write_file(file, s):
    if isinstance(s, str):
        with open(file, 'w') as fp:
            fp.write(s)
    else:
        with io.open(file, 'wb') as fp:
            fp.write(s)


def read_json(file):
    with open(file) as fp:
        return json.load(fp)


def read_file(file, binary=False):
    if binary:
        with io.open(file, 'rb') as fp:
            return fp.read()
    with open(file) as fp:
        return fp.read()


class TestLoader(unittest.TestCase):
# TODO:
# test
#
# entry:
#     plain, utf-8
#     plain, cp-1252
#     image
#     has extension '.jpg', '.mp3', ...
#     has no extension
#
#
# time zone inheritance:
#     from the panel
#     from the entry itself
#
#
# time and datetime parsing:
#     just... test it
#
#
# stuff including
# *   metadata (should be passed on verbatim)
# *   ignored options (a warning in the case of any other option
#                      at entry-level)
#
    def test_basics(self):
        d1 = date(2020, 2, 2)
        d2 = date(2020, 2, 3)
        obj = make_backup([d1, d2])
        obj['desc'] = 'Sus!'
        obj['data'][1]['rating'] = ':('
        obj['data'][0]['tz'] = '+08:00'
        add_entries(
            obj,
            [[
                {
                    'date': '2020-02-04',
                    'time': '01:00',
                    'data': 'First example'
                },
                {
                    'date-time': '2022-02-05 02:00-08:00',
                    'insight': True,
                    'input': 'flareon.txt'
                }
            ],
            [
                {
                    'time': '02:02',
                    'data': 'Second example'
                },
                {
                    'time': '12:34:56',
                    'data': 'Vaporeons are great'
                }
            ]])
        f = ROOT / '0.json'
        flareon = ROOT / 'flareon.txt'
        write_json(f, obj)
        write_file(flareon, 'Flareons are like too fluffy IMO')

        panels = processor.load_json(f)
        (p1, p2) = panels
        self.assertEqual(p1.date, d1)
        self.assertEqual(p2.date, d2)
        self.assertEqual(p1.has_rating(), False)
        self.assertEqual(p2.get_rating(), ':(')
        e1, e2 = p1.get_entries()
        e3, e4 = p2.get_entries()

        self.assertEqual(e1.time.date(), date(2020, 2, 4))
        self.assertEqual(e1.time.time(), time(1))
        self.assertEqual(e1.time.utcoffset(), timedelta(hours=8))
        self.assertEqual(e1.insight, False)
        self.assertEqual(e1.get_data(), 'First example')
        self.assertEqual(e1.get_raw_data(), b'First example')

        text = 'Flareons are like too fluffy IMO'
        self.assertEqual(e2.time.date(), date(2022, 2, 5))
        self.assertEqual(e2.time.time(), time(2))
        self.assertEqual(e2.time.utcoffset(), timedelta(hours=-8))
        self.assertEqual(e2.insight, True)
        self.assertEqual(e2.get_data(), text)
        self.assertEqual(e2.get_raw_data(), text.encode('ascii'))

        self.assertEqual(e3.time.date(), d2)
        self.assertEqual(e3.time.time(), time(2, 2))
        self.assertEqual(e3.time.utcoffset(), timedelta(0))
        self.assertEqual(e3.insight, False)
        self.assertEqual(e3.get_data(), 'Second example')
        self.assertEqual(e3.get_raw_data(), b'Second example')

        self.assertEqual(e4.time.date(), d2)
        self.assertEqual(e4.time.time(), time(12, 34, 56))
        self.assertEqual(e4.time.utcoffset(), timedelta(0))
        self.assertEqual(e4.insight, False)
        self.assertEqual(e4.get_data(), 'Vaporeons are great')
        self.assertEqual(e4.get_raw_data(), b'Vaporeons are great')
        f.unlink()
        flareon.unlink()

    def test_entry_time(self):
        pass

    def test_attributes(self):
        d1 = date(2021, 8, 10)
        obj = make_backup([d1], tz='+08:00')
        add_entries(
            obj,
            [[
                {
                    'time': '09:00',
                    'question': 'Are you sus?',
                    'data': 'no u'
                },
                {
                    'time': '10:00',
                    'type': 'tex',
                    'data': '$e^{i\\pi} + 1 = 0$'
                },
            ]])
        f = ROOT / '0.json'
        write_json(f, obj)

        (p1,) = processor.load_json(f, base_dir=ROOT)
        e1, e2 = p1.entries()

        # Question (None by default)
        self.assertTrue(e1.has_question())
        self.assertEqual(e1.get_question(), 'Are you sus?')
        self.assertFalse(e2.has_question())

        f.unlink()

    def test_lookup_paths(self):
        #
        # ROOT
        # +-- a/
        # |   \-- 1.txt
        # |
        # \-- b/
        #     +-- 1.txt
        #     \-- 2.txt
        #     |
        #     \-- n1/
        #     |   \-- 3.txt
        #     |
        #     \-- nGram/
        #         \-- 4.txt
        #
        a = ROOT / 'a'
        a1 = a / '1.txt'
        b = ROOT / 'b'
        b1 = b / '1.txt'
        b2 = b / '2.txt'
        n1 = b / 'n1'
        n2 = b / 'nGram'
        b3 = n1 / '3.txt'
        b4 = n1 / '4.txt'

        d1 = date(2018, 9, 4)
        d2 = date(2018, 9, 6)
        obj = make_backup([d1])
        paths = obj['paths'] = ['a/']
        edict = {
            'time': '04:00',
            'input': '1.txt',
        }
        add_entries(obj, [[edict]])
        f = ROOT / '0.json'
        write_json(f, obj)
        a.mkdir()
        write_file(a1, 'a1')
        b.mkdir()
        write_file(b1, 'b1')
        write_file(b2, 'b2')
        n1.mkdir()
        n2.mkdir()
        write_file(b3, 'b3')
        write_file(b4, 'b4')

        (panel,) = processor.load_json(f, base_dir=ROOT)
        (entry,) = panel.entries()
        self.assertEqual(entry.get_source(), str(a1))
        self.assertEqual(entry.get_data(), 'a1')

        paths.append('b')
        write_json(f, obj)
        msg = r"found more than one path for {!r}.*"
        with self.assertWarnsRegex(
                processor.LoadWarning, msg.format('1.txt')):
            processor.load_json(f, base_dir=ROOT)
        edict['input'] = '2.txt'
        write_json(f, obj)
        (panel,) = processor.load_json(f, base_dir=ROOT)
        (entry,) = panel.entries()
        self.assertEqual(entry.get_source(), str(b2))
        self.assertEqual(entry.get_data(), 'b2')

        # Option removed

        # other_paths = [paths.pop(), 'b/n*']
        # obj = make_backup([d1, d2])
        # add_entries(
        #     obj,
        #     [[
        #         {
        #             'time': '04:00',
        #             'input': '2.txt'
        #         },
        #         {
        #             'time': '05:00',
        #             'input': '3.txt'
        #         },
        #         {
        #             'time': '06:00',
        #             'input': '4.txt'
        #         }
        #     ]])
        # write_json(f, obj)
        # p1, _ = processor.load_json(f, base_dir=ROOT, paths=other_paths)
        # for entry, filepath, content in zip(
        #         p1.entries(),
        #         (b2, b3, b4),
        #         ('b2', 'b3', 'b4')):
        #     self.assertEqual(entry.get_source(), str(filepath))
        #     self.assertEqual(entry.get_data(), content)

        # obj['data'][0]['entries'][0]['input'] = 'b/2.txt'
        # write_json(f, obj)
        # with self.assertRaises(processor.LoadError):
        #     processor.load_json(f, base_dir=ROOT, paths=other_paths)
        # other_paths.append('.')
        # processor.load_json(f, base_dir=ROOT, paths=other_paths)

        f.unlink()
        shutil.rmtree(a)
        shutil.rmtree(b)

    def test_path_searching(self):
        pass

    def test_load_data(self):
        # TODO:
        # Test if load_data() would change the dict in any way
        obj = make_backup(['2021-12-17'])
        saved = copy.deepcopy(obj)
        # Test if setting time zone in panel would change the time zone
        # Test if


class TestDumper(unittest.TestCase):
# dumping
#
# reverse-inference of type and encoding
# time and datetime
    def test_basics(self):
        outdir = ROOT / '1'
        e1_file = ROOT / 'a.png'
        write_file(e1_file, b'a.png')
        e3_file = ROOT / 'doc' / 'rd.txt'
        e3_file.parent.mkdir()
        write_file(e3_file, 'na\u00efve'.encode('latin-1'))

        tz = timezone(timedelta(hours=8))
        p1 = Panel(date(2021, 12, 16))
        p2 = Panel(date(2021, 12, 17))
        p2.set_rating('QAQ')
        e1 = Entry(datetime(2021, 12, 16, 16, 42, tzinfo=tz))
        e1.set_type('png')
        e1.set_source(e1_file)
        e2 = Entry(datetime(2022, 5, 27, 15, 43, tzinfo=tz), insight=True)
        e2.set_data("i wish i weren't here")
        e3 = Entry(datetime(2021, 12, 17, 13, 24, tzinfo=tz))
        e3.set_type('markdown')
        e3.set_encoding('latin-1')
        e3.set_source(e3_file)
        p1.add_entry(e1)
        p1.add_entry(e2)
        p2.add_entry(e3)

        outdir.mkdir()
        # to mimic the old JSONDumper behavior we have to explicitly
        # provide the paths to be ['assets']
        processor.dump_json([p1, p2], outdir / 'backup.json', base_dir=outdir,
                            paths=['assets'])

        data = read_json(outdir / 'backup.json')
        (p1_json, p2_json), attrs = split_data(data)
        # self.assertRegex(attrs['desc'],
        #                  r'\AThis is a backup file exported at .*\.\Z')
        # attrs.pop('desc')
        self.assertEqual(attrs, {'paths': ['assets']})

        e1_json, e2_json = p1_json.pop('entries')
        e1_path = Path('assets', '2021-12-16_16-42-00')
        self.assertEqual(b'a.png', read_file(outdir / e1_path, True))
        self.assertEqual(p1_json, {'date': '2021-12-16'})
        self.assertEqual(
            e1_json, {
                'time': '16:42+08:00',
                'input': str(e1_path.name),
                'type': 'png'
            })
        self.assertEqual(
            e2_json, {
                'date-time': '2022-05-27 15:43+08:00',
                'insight': True,
                'data': "i wish i weren't here",
            })

        (e3_json,) = p2_json.pop('entries')
        self.assertEqual(
            p2_json,
            {
                'date': '2021-12-17',
                'rating': 'QAQ',
            })
        # Although the entry is encoded with latin-1, it is a text entry
        # so JSONDumper.write_entry_data() should ignore the encoding.
        self.assertEqual(
            e3_json,
            {
                'time': '13:24+08:00',
                'type': 'markdown',
                'data': 'na\u00efve',
            })

        loaded = processor.load_json(outdir / 'backup.json',
                                     base_dir=outdir)
        self.assertTrue(p1 == loaded[0])
        self.assertTrue(p2 == loaded[1])
        e3_file.unlink()
        e3_file.parent.rmdir()
        e1_file.unlink()
        shutil.rmtree(outdir)

    def test_default_time_zone_offset(self):
        # both time and datetime should properly set (with time zone
        # appended to the end) if default time zone is unset or the
        # offset doesn't match
        pass

    def test_path_shortening(self):
# Test 1:
#
#     paths = [ a/*, b/* ]
#     export_paths = [ a/one.md, b/one.md ]
#
#     input_paths should be uneffected (i.e. the same)
#
#
# Test 2:
#
#     paths = [ a/*, b/*, . ]
#     export_paths = [ a/1/one.md, b/one.md ]
#
#     input_paths should be [ 1/one.md, b/one.md ]
#     (remove the . and it should raise a warning that 'b' cannot be found
#     and that you must explicitly append the '.' path)
#
#
# Test 3 (ill-defined paths):
#
#     paths = [ s*, sus ]
#     export_paths = [ sus/tree.txt, s/task.txt ]
#
#     It is possible to use 'tree.txt' and 'task.txt'.
#     (TODO: update JSONLoader so that it doesn't complain about these cases!)
#
#
#
#
#
# Cases where special characters are in the file themselves (like 'a*.txt' and
# 'among_us.txt')
#
# Test 4: (special chars)
#
#     paths = [ a, b ]
#     # Literal asterisk
#     export_paths = [ a/a*.txt, b/among_us.txt ]
#
#     While the dumper is checking for the validity of 'a*.txt', it might
#     accidentally match against 'b/among_us.txt', causing it to use 'a/a*.txt'
#     instead of the shorter path.
#
#     (check for alike cases for ? and []??  Or is it unnecessary...?)
#
        pass
