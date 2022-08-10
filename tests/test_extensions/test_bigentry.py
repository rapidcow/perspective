"""Test the sussy big entries (finally...?)"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import tempfile
import unittest

from psp.extensions import bigentry
from ..test_processors.test_json_processor import (
    make_backup, add_entries, write_json, write_file,
)


def setUpModule():
    global TDIR, ROOT
    TDIR = tempfile.TemporaryDirectory()
    ROOT = Path(TDIR.name)


def tearDownModule():
    TDIR.cleanup()


_FORMAT_TO_EXT = {
    'zip': '.zip',
    'tar': '.tar',
    'gztar': '.tar.gz',
    'bztar': '.tar.bz2',
}


def write_archive(zf_name, arch_format, *args):
    zf_name = Path(zf_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        for name, content in args:
            filename = base / name
            filename.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                with filename.open('wb') as fp:
                    fp.write(content)
            else:
                filename.mkdir()
        shutil.make_archive(zf_name, arch_format, base, '.')
        from subprocess import run
        ext = _FORMAT_TO_EXT[arch_format]
        zf_path = zf_name.parent / f'{zf_name.name}{ext}'
        return zf_path


class TestBigEntry(unittest.TestCase):
    def test_basics(self):
        for arch_format in ('zip', 'tar', 'gztar', 'bztar'):
            arch_name = ROOT / 'a'
            try:
                arch_path = write_archive(
                    arch_name, arch_format,
                    ('main.txt', 'main file'.encode('utf-8')),
                    ('other.txt', 'other file'.encode('utf-8')),
                )
            except ImportError:
                # ???
                continue
            entry = bigentry.BigEntry(datetime(2022, 6, 18, 13, 50,
                                               tzinfo=timezone.utc))
            self.assertTrue(entry.is_text())

            entry.set_source(arch_path)
            entry.set_main_file('main.txt')
            entry.set_main_file_type('plain')
            entry.set_main_file_encoding('utf-8')
            entry.set_type(arch_format)
            self.assertEqual(entry.get_data(), 'main file', msg=arch_format)
            entry.set_main_file(Path(*'among us .. .. other.txt'.split()))
            self.assertEqual(entry.get_data(), 'other file', msg=arch_format)

            arch_path.unlink()


class TestBigLoader(unittest.TestCase):
    def test_basics(self):
        write_archive(
            ROOT / 'a', 'zip',
            ('main.md', b'big entry'),
        )
        obj = make_backup(['2021-01-18'], tz='+08:00')
        add_entries(
            obj,
            [[
                {
                    'time': '15:35',
                    'data': 'small entry'
                },
                {
                    'time': '15:36',
                    'format': 'zip',
                    'data': {
                        'input': 'a.zip',
                        'main-file': 'main.md'
                    }
                }
            ]])
        f = ROOT / '0.json'
        write_json(f, obj)
        loader = bigentry.BigLoader()
        loader.configure(base_dir=ROOT)
        with open(f, encoding='utf-8') as fp:
            loader.load(fp)


class TestBigDumper(unittest.TestCase):
    pass
