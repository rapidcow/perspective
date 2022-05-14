"""Testing the psp.processors.json_processor module."""

from datetime import date, time, timedelta
import json
import os
from os.path import join
import shutil
import sys
import tempfile
import unittest
from psp.processors import json_processor as processor


def setUpModule():
    global _dir_td, _dir
    _dir_td = tempfile.TemporaryDirectory()
    _dir = _dir_td.name


def tearDownModule():
    _dir_td.cleanup()


# Convenience methods for creating JSON backup files
def make_backup(panels=None, tz='UTC'):
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

def write_json(file, obj):
    with open(file, 'w') as fp:
        json.dump(obj, fp)


def write_file(file, s):
    if isinstance(s, str):
        with open(file, 'w') as fp:
            fp.write(s)
    else:
        with open(file, 'wb') as fp:
            fp.write(s)


# Attributes from panels and entries
def get_rating(panel):
    return panel.get_attribute('rating')


def has_rating(panel):
    return panel.has_attribute(panel)


def get_question(entry):
    return entry.get_attribute('question')


def has_question(entry):
    return entry.has_attribute('question')


def get_caption(entry):
    return entry.get_attribute('caption')


def has_caption(entry):
    return entry.has_attribute('caption')


def get_transcription(entry):
    return entry.get_attribute('transcription')


def has_transcription(entry):
    return entry.has_attribute('transcription')


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
        f = join(_dir, '0.json')
        flareon = join(_dir, 'flareon.txt')
        write_json(f, obj)
        write_file(flareon, 'Flareons are like too fluffy IMO')

        panels = processor.load_json(f)
        (p1, p2) = panels
        self.assertEqual(p1.date, d1)
        self.assertEqual(p2.date, d2)
        self.assertEqual(get_rating(p1), None)
        self.assertEqual(get_rating(p2), ':(')
        e1, e2 = p1.get_entries()
        e3, e4 = p2.get_entries()

        self.assertEqual(e1.date_time.date(), date(2020, 2, 4))
        self.assertEqual(e1.date_time.time(), time(1))
        self.assertEqual(e1.date_time.utcoffset(), timedelta(hours=8))
        self.assertEqual(e1.insight, False)
        self.assertEqual(e1.get_data(), 'First example')
        self.assertEqual(e1.get_raw_data(), b'First example')

        text = 'Flareons are like too fluffy IMO'
        self.assertEqual(e2.date_time.date(), date(2022, 2, 5))
        self.assertEqual(e2.date_time.time(), time(2))
        self.assertEqual(e2.date_time.utcoffset(), timedelta(hours=-8))
        self.assertEqual(e2.insight, True)
        self.assertEqual(e2.get_data(), text)
        self.assertEqual(e2.get_raw_data(), text.encode('ascii'))

        self.assertEqual(e3.date_time.date(), d2)
        self.assertEqual(e3.date_time.time(), time(2, 2))
        self.assertEqual(e3.date_time.utcoffset(), timedelta(0))
        self.assertEqual(e3.insight, False)
        self.assertEqual(e3.get_data(), 'Second example')
        self.assertEqual(e3.get_raw_data(), b'Second example')

        self.assertEqual(e4.date_time.date(), d2)
        self.assertEqual(e4.date_time.time(), time(12, 34, 56))
        self.assertEqual(e4.date_time.utcoffset(), timedelta(0))
        self.assertEqual(e4.insight, False)
        self.assertEqual(e4.get_data(), 'Vaporeons are great')
        self.assertEqual(e4.get_raw_data(), b'Vaporeons are great')
        os.unlink(f)
        os.unlink(flareon)

    def test_entry_time(self):
        pass

    def test_attributes(self):
        d1 = date(2021, 8, 10)
        obj = make_backup([d1], tz='+08:00')
        obj['paths'] = ['fig']
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
                    'type': 'markdown',
                    'title': 'The most beautiful equation ever',
                    'data': '$e^{i\\pi} + 1 = 0$'
                },
                {
                    'time': '10:00',
                    'caption': 'A beautiful diagram',
                    'input': 'fig1.jpg'
                },
                {
                    'time': '12:00',
                    'transcription': 'Transcription of something',
                    'input': 'fig2.jpg'
                }
            ]])
        f = join(_dir, '0.json')
        figs = os.path.join(_dir, 'fig')
        fig1 = join(figs, 'fig1.jpg')
        fig2 = join(figs, 'fig2.jpg')
        write_json(f, obj)
        os.mkdir(figs)
        write_file(fig1, b'not really jpeg hehe')
        write_file(fig2, b'again not jpeg')

        (p1,) = processor.load_json(f, base_dir=_dir)
        e1, e2, e3, e4 = p1.entries()

        # Question (unset by default)
        self.assertTrue(has_question(e1))
        self.assertEqual(get_question(e1), 'Are you sus?')
        for e in e2, e3, e4:
            self.assertFalse(e.has_attribute('question'))

        # Title (defaults to None)
        self.assertTrue(e2.has_title())
        self.assertEqual(e2.get_title(), 'The most beautiful equation ever')
        for e in e1, e3, e4:
            self.assertFalse(e.has_title())
            self.assertIs(e.get_title(), None)

        # Caption (unset by default)
        self.assertTrue(has_caption(e3))
        self.assertEqual(get_caption(e3), 'A beautiful diagram')
        for e in e1, e2, e4:
            self.assertFalse(has_caption(e))

        # Transcription (unset by default)
        self.assertTrue(has_transcription(e4))
        self.assertEqual(get_transcription(e4), 'Transcription of something')
        for e in e1, e2, e3:
            self.assertFalse(has_transcription(e))

        os.unlink(f)
        shutil.rmtree(figs)

    def test_lookup_paths(self):
        #
        # _dir
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
        a = os.path.join(_dir, 'a')
        a1 = os.path.join(a, '1.txt')
        b = os.path.join(_dir, 'b')
        b1 = os.path.join(b, '1.txt')
        b2 = os.path.join(b, '2.txt')
        n1 = os.path.join(b, 'n1')
        n2 = os.path.join(b, 'nGram')
        b3 = os.path.join(n1, '3.txt')
        b4 = os.path.join(n1, '4.txt')

        d1 = date(2018, 9, 4)
        d2 = date(2018, 9, 6)
        obj = make_backup([d1])
        paths = obj['paths'] = ['a/']
        edict = {
            'time': '04:00',
            'input': '1.txt',
        }
        add_entries(obj, [[edict]])
        f = join(_dir, '0.json')
        write_json(f, obj)
        os.mkdir(a)
        write_file(a1, 'a1')
        os.mkdir(b)
        write_file(b1, 'b1')
        write_file(b2, 'b2')
        os.mkdir(n1)
        os.mkdir(n2)
        write_file(b3, 'b3')
        write_file(b4, 'b4')

        (panel,) = processor.load_json(f, base_dir=_dir)
        (entry,) = panel.entries()
        self.assertEqual(entry.get_source(), a1)
        self.assertEqual(entry.get_data(), 'a1')

        paths.append('b')
        write_json(f, obj)
        msg = r"found more than one path for {!r}.*"
        with self.assertWarnsRegex(
                processor.LoadWarning, msg.format('1.txt')):
            processor.load_json(f, base_dir=_dir)
        edict['input'] = '2.txt'
        write_json(f, obj)
        (panel,) = processor.load_json(f, base_dir=_dir)
        (entry,) = panel.entries()
        self.assertEqual(entry.get_source(), b2)
        self.assertEqual(entry.get_data(), 'b2')

        other_paths = [paths.pop(), 'b/n*']
        obj = make_backup([d1, d2])
        add_entries(
            obj,
            [[
                {
                    'time': '04:00',
                    'input': '2.txt'
                },
                {
                    'time': '05:00',
                    'input': '3.txt'
                },
                {
                    'time': '06:00',
                    'input': '4.txt'
                }
            ]])
        write_json(f, obj)
        p1, _ = processor.load_json(f, base_dir=_dir, paths=other_paths)
        for entry, filepath, content in zip(
                p1.entries(),
                (b2, b3, b4),
                ('b2', 'b3', 'b4')):
            self.assertEqual(entry.get_source(), filepath)
            self.assertEqual(entry.get_data(), content)

        obj['data'][0]['entries'][0]['input'] = 'b/2.txt'
        write_json(f, obj)
        with self.assertRaises(processor.LoadError):
            processor.load_json(f, base_dir=_dir, paths=other_paths)
        other_paths.append('.')
        processor.load_json(f, base_dir=_dir, paths=other_paths)

        os.unlink(f)
        shutil.rmtree(a)
        shutil.rmtree(b)


class TestDumper(unittest.TestCase):

# dumping
#
# reverse-inference of type and encoding
# time and datetime
# loaded result == dumped objects

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
