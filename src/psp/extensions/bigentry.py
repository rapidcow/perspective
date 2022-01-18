"""Big entry extension."""
# XXX: Still mainly experimental...

import base64
import collections
import io
import os
import tarfile
import tempfile
import zipfile

from .. import Entry
from .. import datatypes
from ..processors import JSONLoader, JSONDumper

__all__ = [
    'BigEntry', 'BigLoader', 'BigDumper', 'load', 'dump',
]


# Archive format is essentially a subset of the DATA TYPES.
_ARCHIVE_FORMATS = [
    'zip', 'tar', 'gztar', 'bztar',
]

#
# Some differences compared to psp.Entry:
#
# Several data attributes added:
#
#     main_file             main file path within the archive
#     main_file_type        type of main file (must be a text type)
#     main_file_encoding    encoding of main file (must not be binary)
#     main_file_format      optional
#
# Their corresponding getters/setters are set_*() and get_*().
#
# Attributes removed: question, caption
#
#
# Some additional remarks:
#
#   *   is_text() returns True.
#
#   *   The old data-related functions (get_type(), get_encoding(),
#       get_format(), get_source()) return information about the whole
#       archive.
#
#   *   get_data() returns the text from the main file (for stringify to
#       somewhat properly work).  get_raw_data() still works as expected.
#
class BigEntry(Entry):
    __slots__ = ()

    def __init__(self, panel, date_time, *, insight=False):
        super().__init__(panel, date_time, insight=insight)
        self.set_main_file_type('plain')
        self.set_main_file_encoding('utf-8')
        self.set_main_file_format(None)

    def is_text(self):
        return True

    def get_data(self):
        if self.has_raw_data():
            # We would like to close the file pointer by the time we re-open
            # the temporary file in __extract_data_from_filename(), but also
            # we don't want the file to be deleted by the time we close the
            # pointer.  That's where the delete=False comes in... (i guess)
            fp = tempfile.NamedTemporaryFile(delete=False)
            try:
                with fp:
                    fp.write(self.get_raw_data())
                return self.__extract_data_from_filename(fp.name)
            finally:
                os.unlink(fp.name)
        else:
            return self.__extract_data_from_filename(self.get_source())

    def __extract_data_from_filename(self, filename):
        arch_format = self.get_type()
        mf_name = self.get_main_file()
        enc = self.get_main_file_encoding()
        if arch_format == 'zip':
            with zipfile.ZipFile(filename) as zf:
                with zf.open(mf_name) as mainfp:
                    return mainfp.read().decode(enc)
        if arch_format in {'tar', 'gztar', 'bztar'}:
            with tarfile.open(filename) as tf:
                info = tf.getmember(mf_name)
                with tf.extractfile(info) as mainfp:
                    return mainfp.read().decode(enc)
        # This shouldn't happen...?
        raise ValueError(f'unknown archive format: {arch_format!r}')

    # Getters and setters (the rather boring part, you can say)
    def set_main_file(self, value):
        super().set_data_attribute('mf_name', value)

    def get_main_file(self):
        return super().get_data_attribute('mf_name')

    def set_type(self, value):
        if value not in _ARCHIVE_FORMATS:
            raise ValueError(f'invalid archive format: {value!r}')
        super().set_type(value)

    def set_main_file_type(self, value):
        super().set_data_attribute('mf_type', value)

    def get_main_file_type(self):
        return super().get_data_attribute('mf_type')

    def set_main_file_encoding(self, value):
        super().set_data_attribute('mf_encoding', value)

    def get_main_file_encoding(self):
        return super().get_data_attribute('mf_encoding')

    def set_main_file_format(self, value):
        super().set_data_attribute('mf_format', value)

    def get_main_file_format(self):
        return super().get_data_attribute('mf_format')

    def set_data_attribute(self, key, value):
        if key == 'mf_name':
            self.set_main_file(value)
        elif key == 'mf_type':
            self.set_main_file_type(value)
        elif key == 'mf_encoding':
            self.set_main_file_encoding(value)
        elif key == 'mf_format':
            self.set_main_file_format(value)
        else:
            super().set_data_attribute(key, value)

    # Prevent attributes 'question' and 'caption' from being set
    def set_attribute(self, key, value):
        if key in {'question', 'caption'}:
            raise ValueError(f'cannot set key for big entry: {key!r}')
        super().set_attribute(key, value)


#
# The only difference this loader makes is when an entry dict contains
# a dictionary for 'data'.  In that case, the dictionary must provide
#
#   *   Precisely one of 'raw' and 'input' (similar to 'data' and 'input');
#       and
#   *   The path of the main file within the archive, through 'main-file'.
#
# The 'input' attribute, if provided, should be a path to the archive.
# The 'raw' attribute, if provided, should a base64-encoded ASCII string.
#
# At the topmost level of entry (the same level as the 'time' and 'data'
# attribute), 'type' and 'encoding' are not allowed.  The 'format' takes
# on a different role, though: the archive format mentioned above.
#
# Here is an overview of all the attributes specific to big entries that
# you can specify (aside from the 'date-time' one, i added it so that it
# looks better or something idk)
#
#     {
#         "date-time": "2021-12-17 ",
#         "format": "the archive format",
#         "data": {
#             "input": "the path to the archive",
#             "main-file": "main file within archive",
#             "type": "type of the main file",
#             "encoding": "encoding of the main file",
#             "format": "format of the main file"
#         }
#     }
#
# The inference rules will work as expected!  (I hope when i implement it
# it does...)  So if 'main-file' is 'main.md', then you can expect the main
# file type to be 'markdown'.
#
class BigLoader(JSONLoader):
    __slots__ = ()

    def process_entry(self, panel, entry, attrs):
        if not ('data' in entry and isinstance(entry['data'], dict)):
            return super().process_entry(panel, entry, attrs)

        arch_data = entry.pop('data')
        # Raise exception for extraneous keys
        if any(k in entry for k in {'input', 'type', 'encoding'}):
            raise ValueError(f'invalid key for entry: {k!r}')
        if any(k in arch_data for k in {'data', 'data-encoding'}):
            raise ValueError(f'invalid key for archive data: {k!r}')

        # Get the important things: archive format and main file path,
        # also transfer the raw data/source path to 'entry' so we can use
        # the super process_entry() to parse the entry normally.
        main_file = arch_data.pop('main-file')
        arch_format = entry.pop('format', None)
        if 'input' in arch_data and 'raw' in arch_data:
            raise ValueError('exactly one of input and raw can be '
                             'specified in archive data')
        if 'input' in arch_data:
            arch_path = entry['input'] = arch_data.pop('input')
            if arch_format is None:
                arch_format = datatypes.path_to_type(arch_path)
        elif 'raw' in arch_data:
            entry['data'] = arch_data.pop('raw')
            entry['data-encoding'] = 'base64'

        if arch_format is None:
            raise ValueError('unable to infer archive format; '
                             'must be explicitly specified')
        if arch_format not in _ARCHIVE_FORMATS:
            raise ValueError(f'file type not an archive: {arch_format!r}')
        entry['type'] = arch_format

        parsed = super().process_entry(panel, entry, attrs)
        obj = BigEntry.from_entry(parsed)

        # Extracting type, encoding and format from archive data
        if 'type-format' in arch_data:
            mf_type, mf_format = arch_data.pop('type-format').split('-')
        else:
            mf_type = arch_data.pop('type', None)
            mf_format = arch_data.pop('format', None)
        # Inference
        mf_encoding = arch_data.pop('encoding', None)
        if mf_type is None:
            mf_type = datatypes.path_to_type(main_file, default='plain')
        if mf_encoding is None:
            mf_encoding = 'utf-8'

        # Validation
        if mf_encoding == 'binary':
            raise ValueError('encoding must not be binary (main file '
                             'should be a text file)')

        obj.set_main_file(main_file)
        obj.set_main_file_type(mf_type)
        obj.set_main_file_encoding(mf_encoding)
        obj.set_main_file_format(mf_format)

        if arch_data:
            remaining = ', '.join(sorted(map(str, arch_data.keys())))
            self._warn(f'ignored archive data keys: {remaining}',
                       RuntimeWarning)
        return obj


# Big entries, by default, are exported to the 'doc' directory.
# This can be overriden by overriding get_entry_filename() (so that it
# returns None on the entries you want to keep) or by using the basic_dump()
# interface.
class BigDumper(JSONDumper):
    __slots__ = ()

    def __init__(self, **options):
        super().__init__()
        self.configure(paths=self.get_option('paths') + ('doc',))
        self.configure(**options)

    def get_entry_filename(self, entry, panel, added):
        if isinstance(entry, BigEntry):
            root, filename = super().get_basic_entry_filename(
                entry, panel, added)
            return root, os.path.join('doc', filename)
        return super().get_entry_filename(entry, panel, added)

    def write_entry_data(self, entry_dict, entry):
        del entry_dict['type']
        del entry_dict['encoding']
        if not isinstance(entry, BigEntry):
            return super().write_entry_data(entry_dict, entry)
        entry_dict['format'] = entry.get_type()
        data_dict = entry_dict['data'] = collections.OrderedDict()
        encoded_data = base64.b64encode(entry.get_raw_data())
        data_dict['raw'] = encoded_data.decode('ascii')
        self.__write_main_file_data(data_dict, entry)

    def export_entry(self, entry_dict, entry, export_path, input_path):
        super().export_entry(entry_dict, entry, export_path, input_path)

        if isinstance(entry, BigEntry):
            entry_dict.pop('type', None)
            assert 'encoding' not in entry_dict
            inferred_type = datatypes.path_to_type(input_path, default=None)
            arch_type = entry.get_type()
            if inferred_type is None or inferred_type != arch_type:
                entry_dict['format'] = arch_type

            data_dict = entry_dict['data'] = collections.OrderedDict()
            data_dict['input'] = entry_dict.pop('input')
            # print('inside export_entry, entry_dict is now', entry_dict)
            self.__write_main_file_data(data_dict, entry)
            if 'meta' in entry_dict:
                entry_dict.move_to_end('meta')

    def __write_main_file_data(self, data_dict, entry):
        assert isinstance(entry, BigEntry)
        filename = data_dict['main-file'] = entry.get_main_file()
        # Reverse inference... who wants it?
        type_ = entry.get_main_file_type()
        enc = entry.get_main_file_encoding()
        format_ = entry.get_main_file_format()

        inferred_type = datatypes.path_to_type(filename, default='plain')
        if format_ is not None:
            data_dict['type-format'] = type_ + '-' + format_
        elif inferred_type != type_:
            data_dict['type'] = type_
        if enc != 'utf-8':
            data_dict['encoding'] = enc


def load(file, **kwargs):
    loader = BigLoader(**kwargs)
    return loader.load(file)


def dump(panels, dirname, **kwargs):
    dumper = BigDumper(**kwargs)
    return dumper.dump(panels, dirname)
