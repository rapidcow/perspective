"""Test big entries"""
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest

from . import *
from psp.types import Entry
from psp.serializers import JSONDumper
from psp.ext.bigentry import BigDumper, BigEntry


def can_pack_format(fmt):
    for arch_format, _ in shutil.get_archive_formats():
        if arch_format == fmt:
            return True
    return False


def create_zip(*files):
    with make_tempdir() as tmp:
        zip_base = tmp / 'foo'
        for file, content in files:
            if isinstance(content, str):
                with open_with_unicode(tmp / file, 'w') as fp:
                    fp.write(content)
            else:
                with (tmp / file).open('wb') as fp:
                    fp.write(content)
        zip_path = shutil.make_archive(zip_base, 'zip', tmp, tmp)
        with open(zip_path, 'rb') as fp:
            return fp.read()


class TestBigDumper(unittest.TestCase):
    @tempdir
    @unittest.skipIf(not can_pack_format('zip'), 'shutil cannot unpack zip')
    def test_ii(self, root):
        """Test big dumper exporting"""
        class SomeBigDumper(BigDumper):
            __slots__ = ()
            def get_export_path_directory(self, entry):
                if entry.get_type() == 'jpeg':
                    return ('img', '')
                return super().get_export_path_directory(entry)

            # force text files to be exported too
            def use_inline_text(self, entry):
                return False

        dumper = SomeBigDumper(base_dir=root)
        attrs = dumper.get_top_level_attributes([])

        # 1. if big entry, then export to doc
        entry = BigEntry(make_time('2021-12-17 03:50:00+0000'))
        entry.set_type('zip')
        entry.set_raw_data(create_zip(['main.txt', 'hello from main.txt']))
        entry.set_main_file('main.txt')
        entry.set_main_file_type('plain')
        entry.set_main_file_encoding('utf-8')
        self.assertEqual(dumper.wrap_entry(entry, attrs), {
                'date-time': '2021-12-17 03:50+00:00',
                'format': 'zip',
                'data': {
                    'input': 'doc/2021-12-17_03-50-00',
                    'main-file': 'main.txt'
                }
            })
        with open(root / 'doc' / '2021-12-17_03-50-00', 'rb') as fp:
            self.assertEqual(fp.read(), entry.get_raw_data())

        # 2. otherwise do nothing
        jpeg_entry = Entry(make_time('2022-02-18 16:16:16+0800'))
        text_entry = jpeg_entry.copy()

        jpeg_entry.set_type('jpeg')
        jpeg_entry.set_raw_data(b'not really a jpeg')
        text_entry.set_data('something', type='plain', encoding='utf-8')

        self.assertEqual(dumper.wrap_entry(jpeg_entry, attrs), {
                'date-time': '2022-02-18 16:16:16+08:00',
                'type': 'jpeg',
                'input': 'img/2022-02-18_16-16-16'
            })
        with open(root / 'img' / '2022-02-18_16-16-16', 'rb') as fp:
            self.assertEqual(fp.read(), jpeg_entry.get_raw_data())

        self.assertEqual(dumper.wrap_entry(text_entry, attrs), {
                'date-time': '2022-02-18 16:16:16+08:00',
                'input': 'assets/2022-02-18_16-16-16.txt'
            })
        with open_with_unicode(
                root / 'assets' / '2022-02-18_16-16-16.txt') as fp:
            self.assertEqual(fp.read(), text_entry.get_data())



class TestBigEntryManager(unittest.TestCase):
    """Test default big entry managers"""
    @tempdir
    def test_pull_request_005(self, root):
        """TrellixVulnTeam's security fix
        https://github.com/rapidcow/perspective/pull/5
        """
        for tar_format, mode in [('tar', ''), ('gztar', ':gz'),
                                 ('bztar', ':bz2'), ('xztar', ':xz')]:
            if BigEntry.has_manager(tar_format):
                if not can_pack_format(tar_format):
                    # i don't know how to use logging lol
                    print(f'INFO: shutil cannot pack {tar_format}, '
                          f'skipping the test', file=sys.stderr)
                    continue
                filepath = root / 'foo'
                target = root / 'very' / 'deep' / 'directory'
                target.mkdir(parents=True)

                with open_with_unicode(root / 'bar.txt', 'w') as fp:
                    fp.write('a bar file')
                with open_with_unicode(root / 'main.txt', 'w') as fp:
                    fp.write('a main file')
                with tarfile.open(filepath, f'w{mode}') as tf:
                    tf.add(root / 'bar.txt', '../bar.txt')
                    tf.add(root / 'main.txt', 'main.txt')

                entry = BigEntry(make_time('2022-02-22 14:40:00+0000'))
                entry.set_source(filepath)
                entry.set_type(tar_format)
                entry.set_main_file('main.txt')
                # entry.set_main_file_type('plain')
                # entry.set_main_file_encoding('utf-8')
                msg = 'attempted path traversal in tar file'
                with self.assertRaisesRegex(ValueError, msg):
                    entry.extract_all(target)
                filepath.unlink()
                shutil.rmtree(root / 'very')
