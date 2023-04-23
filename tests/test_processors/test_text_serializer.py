"""Test... text serializer"""
import datetime
from textwrap import dedent
import unittest
import psp.serializers.text as text

import logging

# logging.getLogger('psp.serializers.text').setLevel(logging.DEBUG)


class TestTextLoader(unittest.TestCase):
    maxDiff = 10000

    def test_documentation(self):
        # whitespace should have no effect on time parsing
        loader = text.TextLoader()
        data = loader.loads(dedent("""\
        DATE apr  1      2023
                TIME      12:30

        <<<
             five spaces and  two spaces
        >>>
        """))
        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-04-01',
                'entries': [{
                  'time': '12:30',
                  'data': '     five spaces and  two spaces\n',
                }]
              }]
            })

        # testing multiline strings
        data = loader.loads(dedent("""\
        Date apr 14 2023
        Time 7:43
        <<<
        this should be where the content begins
        i mean
        it's cool
        that i can write stuff in here
        >>>

        Time 1:30 pm
        <<<<< markdown
            this is a **Markdown** entry\x20\t\x20
        with many
          <<<
        and
            >>>
        >>>>>
        """))

        content1 = dedent("""\
        this should be where the content begins
        i mean
        it's cool
        that i can write stuff in here
        """)
        content2 = dedent("""\
            this is a **Markdown** entry\x20\t\x20
        with many
          <<<
        and
            >>>
        """)
        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-04-14',
                'entries': [
                  {
                    'time': '07:43',
                    'data': content1,
                  },
                  {
                    'time': '13:30',
                    'type': 'markdown',
                    'data': content2,
                  }
                ]
              }]
            })


        data = loader.loads(dedent("""\
        DATE Apr 21 2023
        TIME 22:40
        <<<<<
        content began with five <'s, so we'd expect five >'s
        not this:
        >>>
        or any this:
        >>>>>>>>
        >>>>> i like trains
        but precisely, this:
        >>>>>
        """))

        content = dedent("""\
        content began with five <'s, so we'd expect five >'s
        not this:
        >>>
        or any this:
        >>>>>>>>
        >>>>> i like trains
        but precisely, this:
        """)

        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-04-21',
                'entries': [{
                  'time': '22:40',
                  'data': content,
                }]
              }]
            })

        # test custom attributes

        data = loader.loads(dedent("""\
        DATE APRIL 1 2023
        # panel attributes
        RATING :D
        ATTR {
          "custom-attribute": "foo!"
        }

        TIME 12:30
        # entry attributes
        TYPE markdown
        FORMAT pandoc
        QUESTION How was your day?
        <<<
        ok!
        >>>
        ATTR {
          "custom-attribute": "bar!"
        }
        """))

        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-04-01',
                'rating': ':D',
                'custom-attribute': 'foo!',
                'entries': [{
                    'time': '12:30',
                    'type': 'markdown',
                    'format': 'pandoc',
                    'question': 'How was your day?',
                    'data': 'ok!\n',
                    'custom-attribute': 'bar!'
                }]
              }]
            })

        # TEST ERRORS?
        # error on unknown panel
        # error on unknown entry
        # error on unknown year
        # error on EOF in the process of scanning for >>>...
