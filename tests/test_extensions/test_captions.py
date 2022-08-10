from datetime import date
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from psp.extensions import captions
from ..test_processors.test_json_processor import (
    make_backup, add_entries, write_json, write_file)


def setUpModule():
    global TDIR, ROOT
    TDIR = tempfile.TemporaryDirectory()
    ROOT = Path(TDIR.name)


def tearDownModule():
    TDIR.cleanup()


class TestCaptionLoader(unittest.TestCase):
    def test_attribute(self):
        d1 = date(2020, 2, 2)
        obj = make_backup([d1])
        obj['paths'] = ['fig']
        add_entries(
            obj,
            [[
                {
                    'time': '10:00',
                    'caption': 'A beautiful diagram',
                    'input': 'fig1.jpg'
                },
                {
                    'time': '12:00',
                    'title': 'My first entry with a fancy title',
                    'transcription': 'Transcription of something',
                    'input': 'fig2.jpg'
                },
            ]])
        f = ROOT / '0.json'
        write_json(f, obj)
        figs = ROOT / 'fig'
        fig1 = figs / 'fig1.jpg'
        fig2 = figs / 'fig2.jpg'
        figs.mkdir()
        write_file(fig1, b'not really jpeg hehe')
        write_file(fig2, b'again not jpeg')

        with open(f, encoding='utf-8') as fp:
            (panel,) = captions.CaptionJSONLoader(base_dir=ROOT).load(fp)
        e1, e2 = panel.entries()

        # Caption
        self.assertTrue(e1.has_caption())
        self.assertEqual(e1.get_caption(), 'A beautiful diagram')
        self.assertFalse(e2.has_caption())

        # Transcription
        self.assertTrue(e2.has_transcription())
        self.assertEqual(e2.get_transcription(), 'Transcription of something')
        self.assertFalse(e1.has_transcription())

        # Title
        self.assertTrue(e2.has_title())
        self.assertEqual(e2.get_title(), 'My first entry with a fancy title')
        self.assertFalse(e1.has_title())

        f.unlink()
        shutil.rmtree(figs)


class TestCaptionFormatter(unittest.TestCase):
    def test_entry_title(self):
        pass

    def test_caption(self):
        pass

    def test_transcription(self):
        pass


if __name__ == '__main__':
    unittest.main()
