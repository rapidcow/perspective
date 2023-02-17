"""Test big entries"""
import shutil
import sys
import tarfile
import unittest

from . import *
from psp.extensions.bigentry import BigEntry


class TestBigEntryManager(unittest.TestCase):
    @tempdir
    def test_pull_request_005(self, root):
        # TrellixVulnTeam's security fix
        # https://github.com/rapidcow/perspective/pull/5

        arch_formats = [f for f, _ in shutil.get_archive_formats()]
        for tar_format in [('tar', ''), ('gztar', ':gz'),
                           ('bztar', ':bz2'), ('xztar', ':xz')]:
            if BigEntry.has_manager(tar_format):
                if tar_format not in arch_formats:
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
                with tarfile.open(filepath, mode) as tf:
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
