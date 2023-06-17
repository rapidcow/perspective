"""Test... text serializer"""
import datetime
from textwrap import dedent
import logging
import unittest
import psp.serializers.text as text
from psp.ext.bigentry import BigTextLoader
from psp.ext.metadata import MetaTextLoader
from psp.ext.captions import CaptionTextLoader

# logging.getLogger('psp.serializers.text').setLevel(logging.DEBUG)


class TestTextLoader(unittest.TestCase):
    maxDiff = 10000

    def test_documentation(self):
        # some vile file
        loader = text.TextLoader()
        # text._DEBUG = 69
        data = loader.loads(dedent("""\
        # shell-like comments are supported! :D
        YEAR 2023           # default year
        TIME ZONE +08:00    # corresponds to the "tz" field
        PATHS [".", "doc"]  # corresponds to the "paths" field

        DATE Mar 14 :(
        TIME 3:29 pm
        <<< markdown
        this  is an  entry with   *s t u f f*
        # this is not a comment
        >>>

        TIME Mar 15 18:20
        QUESTION what are you
        TYPE plain
        INPUT someVileFile.txt

        DATE Feb 14 2022
        INSIGHT Mar 15 2023 5:17 pm
        <<<
        oh
          and
            many lines too
        >>>
        """))
        self.assertEqual(
            data, {
              'tz': '+08:00',
              'paths': [ '.', 'doc' ],
              'year': 2023,
              'data': [
                {
                  'date': '2023-03-14',
                  'rating': ':(',
                  'entries': [
                    {
                      'time': '15:29',
                      'type': 'markdown',
                      'data': ('this  is an  entry with   *s t u f f*\n'
                               '# this is not a comment\n')
                    },
                    {
                      'date-time': '2023-03-15 18:20',
                      'question': 'what are you',
                      'type': 'plain',
                      'input': 'someVileFile.txt'
                    }
                  ]
                },
                {
                  'date': '2022-02-14',
                  'entries': [
                    {
                      'date-time': '2023-03-15 17:17',
                      'insight': True,
                      'data': 'oh\n  and\n    many lines too\n'
                    }
                  ]
                }
              ]
            })

        # whitespace should have no effect on time parsing
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

    def test_custom_attrs(self):
        loader = text.TextLoader()
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

        # ratings
        data = loader.loads(dedent("""\
        DATE APRIL 1 2023 :(
        DATE APRIL 2 2023 O o
        """))

        self.assertEqual(
            data, {
              'data': [
                {
                  'date': '2023-04-01',
                  'rating': ':('
                },
                {
                  'date': '2023-04-02',
                  'rating': 'O o'
                }
              ]
            })

        # TEST ERRORS?
        # error on unknown panel
        # error on unknown entry
        # error on unknown year
        # error on EOF in the process of scanning for >>>...

    def test_random_s__t(self):
        loader = text.TextLoader()
        data = loader.loads(dedent("""\
        date apr 14 2023
        time 7:43
        <
        this should be where the content begins
        i mean\x20
        it's   \\cool
        that i can write stuff in here \\
        >

            TIMe 1:30 pm
            type 1234
            <<<<< markdown
                this is a **Markdown** entry\x20\t\x20
            with many
            <<<
            and
            >>>
            >>>>> \t \t \t
        """))

        self.assertEqual(
            data, {
              'data': [{
               'date': '2023-04-14',
               'entries': [
                  {
                    'time': '07:43',
                    'data': ('this should be where the content begins\n'
                             'i mean \n'
                             "it's   \\cool\n"
                             'that i can write stuff in here \\\n')
                  },
                  {
                    'time': '13:30',
                    'type': 'markdown',
                    'data': ('        this is a **Markdown** entry \t \n'
                             '    with many\n'
                             '    <<<\n'
                             '    and\n'
                             '    >>>\n')
                  }
                ]}
              ]
            })


        data = loader.loads(dedent("""\
        daTe 'march'  03\ \ 2023
        TimE   12":"30  'A'"m"
        <
        hi
        >
        """))

        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-03-03',
                'entries': [{
                  'time': '00:30',
                  'data': 'hi\n',
                }]
              }]
            })

    # XXX should CRLF / CR line terminators even be supported.....
    def test_extensions(self):
        data = BigTextLoader().loads("""\
TIME ZONE Asia/Hong_Kong
YEAR 2023  # L + ratio
desc <<<|
please stop hitting my ribcage with a metal bar\r\
ouchie, gooie, yikes!
>>>
ATTR { "ratio": [5, 19] }
DATE Apr 21 >:*
TIME 22:40
INPUT some-path.zip
MAIN-FILE some
MF-TYPE markdown
MF-FORMAT pandoc

TIME Apr 22 03:50
DATA aSBsb3ZlIHlvdSA8Mw==
MAIN-FILE some other
""")

        self.assertEqual(
            data, {
              'tz': 'Asia/Hong_Kong',
              'year': 2023,
              'desc': ('please stop hitting my ribcage with a metal bar\r'
                       'ouchie, gooie, yikes!'),
              'ratio': [5, 19],
              'data': [{
                'date': '2023-04-21',
                'rating': '>:*',
                'entries': [
                  {
                    'time': '22:40',
                    'data': {
                      'input': 'some-path.zip',
                      'main-file': 'some',
                      'type': 'markdown',
                      'format': 'pandoc'
                    }
                  },
                  {
                    'date-time': '2023-04-22 03:50',
                    'data': {
                      'raw': 'aSBsb3ZlIHlvdSA8Mw==',
                      'main-file': 'some other'
                    }
                  }
                ]
              }]
            })

        data = CaptionTextLoader().loads(dedent("""\
        DATE Apr 21 2023
        TIME 22:40
        INPUT some-path.jpg
        TYPE jpeg
        TITLE the story of my great    corgi  # it is true
        CAPTION   A kind of  secret  image    # not really
        TRANSCRIPTION <<<
        [The corgi jumps into the air, her mouth holding a rubber ball.]
        [Taken with a ... I don't know, I forgot.]
        >>>
        """))

        self.assertEqual(
            data, {
              'data': [{
                'date': '2023-04-21',
                'entries': [{
                  'time': '22:40',
                  'input': 'some-path.jpg',
                  'type': 'jpeg',
                  'title': 'the story of my great corgi',
                  'caption': 'A kind of secret image',
                  'transcription': ('[The corgi jumps into the air, '
                                    'her mouth holding a rubber ball.]\n'
                                    "[Taken with a ... I don't know, "
                                    'I forgot.]\n')
                }]
              }]
            })

        class MyLoader(CaptionTextLoader, MetaTextLoader):
            pass

        data = MyLoader(attrs={'tz': '+08:00'}).loads(
        dedent("""\
        # A comment
        # Another comment
        YEAR 2020
        PATHS ["../img"]
        ---------------
        DATE May 20
        TIME 04:05 PM
        INPUT ps-discussion.jpg
        CAPTION Intelligent response involving the use \
                of perfectly grammatical words
        META { "created": "2020-02-21 16:05:09" }
        META {
          "desc": "Screenshot (they suck btw)"
        }
        """))

        self.assertEqual(
            data, {
              'year': 2020,
              'tz': '+08:00',
              'paths': ['../img'],
              'data': [{
                'date': '2020-05-20',
                'entries': [{
                  'time': '16:05',
                  'input': 'ps-discussion.jpg',
                  'caption': ('Intelligent response involving the '
                              'use of perfectly grammatical words'),
                  'meta': {
                    'created': '2020-02-21 16:05:09',
                    'desc': 'Screenshot (they suck btw)'
                  }
                }]
              }]
            })

    def test_weirdos(self):
        # this is technically an illegal entry
        # but welp, at least it reveals a buggy behavior
        loader = text.TextLoader()
        data = loader.loads(dedent("""\
        DATE June 18 2023
        TIME 04:46
        """))
        # from pprint import pp
        # pp(data)
