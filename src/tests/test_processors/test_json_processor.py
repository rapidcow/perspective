"""Testing the psp.processors.json_processor module."""

import datetime
import json
import os
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


class TestLoader(unittest.TestCase):
    _ = """
test

entry:
    plain, utf-8
    plain, cp-1252
    image
    has extension '.jpg', '.mp3', ...
    has no extension


time zone inheritance:
    from the panel
    from the entry itself


time and datetime parsing:
    just... test it




dumping

reverse-inference of type and encoding
time and datetime
loaded result == dumped objects
"""

    del _

    def test_basic(self):
        bk1 = os.path.join(_dir, '1.json')
        with open(bk1, 'w') as fp:
            fp.write("""{
              "desc": "Sus!",
              "tz": "+00:00",
              "data": [
                {
                  "date": "2020-02-02",
                  "rating": ":(",
                  "entries": [
                    {
                      "time": "02:02",
                      "data": "First example..."
                    },
                    {
                      "time": "12:34:56",
                      "data": "Vaporeons are great"
                    }
                  ]
                }
              ]
            }""")

        attrs, panels = processor.load_json(bk1, get_attributes=True)
        self.assertEqual(attrs, {'desc': 'Sus!', 'tz': '+00:00'})
        p1 = panels[0]
        self.assertEqual(p1.date, datetime.date(2020, 2, 2))
        e = list(p1.get_entries())
        e1 = e[0]
        e2 = e[1]
        self.assertEqual(e1.date_time.date(), p1.date)
        self.assertEqual(e1.date_time.time(), datetime.time(2, 2))
        self.assertEqual(e1.get_data(), 'First example...')
        self.assertEqual(e1.get_raw_data(), b'First example...')
        # self.assertEqual(e1.data['raw'], b'First example...')

        self.assertEqual(e2.date_time.date(), p1.date)
        self.assertEqual(e2.date_time.time(), datetime.time(12, 34, 56))
        self.assertEqual(e2.get_data(), 'Vaporeons are great')
        self.assertEqual(e2.get_raw_data(), b'Vaporeons are great')
        # self.assertEqual(e2.data['raw'], b'Vaporeons are great')

    # TODO: Test more after specifications are written out


class TestDumper(unittest.TestCase):
    def test_path_shortening(self):
        pass


        test = """
Test 1:

    paths = [ a/*, b/* ]
    export_paths = [ a/one.md, b/one.md ]

    input_paths should be uneffected (i.e. the same)


Test 2:

    paths = [ a/*, b/*, . ]
    export_paths = [ a/1/one.md, b/one.md ]

    input_paths should be [ 1/one.md, b/one.md ]
    (remove the . and it should raise a warning that 'b' cannot be found
    and that you must explicitly append the '.' path)


Test 3 (ill-defined paths):

    paths = [ s*, sus ]
    export_paths = [ sus/tree.txt, s/task.txt ]

    It is possible to use 'tree.txt' and 'task.txt'.
    (TODO: update JSONLoader so that it doesn't complain about these cases!)





Cases where special characters are in the file themselves (like 'a*.txt' and
'among_us.txt')

Test 4: (special chars)

    paths = [ a, b ]
    # Literal asterisk
    export_paths = [ a/a*.txt, b/among_us.txt ]

    While the dumper is checking for the validity of 'a*.txt', it might
    accidentally match against 'b/among_us.txt', causing it to use 'a/a*.txt'
    instead of the shorter path.

    (check for alike cases for ? and []??  Or is it unnecessary...?)

"""

        del test
