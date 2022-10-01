"""Blog-style entries."""

import abc
import base64
import collections
from contextlib import contextmanager
import io
import os
import tarfile
import shutil
import tempfile
import zipfile

from psp.processors.json_processor import JSONLoader, JSONDumper
from psp.types import Entry

__all__ = [
    'BigEntry', 'BigLoader', 'BigDumper', 'load', 'dump',
]


class BigEntryManager(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def extract_all(self, entry, dirpath):
        pass

    def get_main_file_data(self, entry):
        mf_name = entry.get_main_file()
        mf_enc = entry.get_main_file_encoding()
        with TemporaryDirectory() as tdir:
            self.extract_all(entry, tdir)
            try:
                with io.open(os.path.join(tdir, mf_name),
                             encoding=mf_enc) as fp:
                    return fp.read()
            except OSError as exc:
                raise ValueError(f'cannot find main file '
                                 f'{mf_name!r}') from exc

    def stream_main_file_data(self, entry):
        return io.StringIO(self.get_main_file_data(entry))


BUFSIZE = 8192

#
# Some differences compared to psp.types.Entry:
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
#    *  is_text() returns True.
#
#    *  The old data-related functions (get_type(), get_encoding(),
#       get_format(), get_source()) return information about the whole
#       archive.
#
#    *  get_data() returns the text from the main file (for stringify to
#       somewhat properly work).  get_raw_data() still works as expected.
#
class BigEntry(Entry, extname='big'):
    __slots__ = ()
    _big_managers = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_encoding('binary')
        self.set_format(None)
        # main_file is not set by default...
        self.set_main_file_type('plain')
        self.set_main_file_encoding('utf-8')
        self.set_main_file_format(None)

    def is_text(self):
        return True

    def __get_manager(self):
        arc_format = self.get_type()
        try:
            manager = self.get_manager(arc_format)
        except KeyError:
            raise ValueError(f'unknown archive format: '
                             f'{arc_format!r}') from None
        return manager

    # BigEntry reimplements this, where get_data() returns the data from
    # the main file but export() writes a zip archive (to keep the
    # compatibility with the promise of the 'file' argument being a file
    # and not a directory)
    #
    # (i copy-and-pasted this from types.py lol)
    def get_data(self):
        return self.__get_manager().get_main_file_data(self)

    def stream_data(self):
        return self.__get_manager().stream_main_file_data(self)

    # Since big entries are inheritly binary files, equality for big entries
    # has to take the equality of the raw data into account
    def __eq__(self, other):
        # XXX: But should a non-big entry be equal to a big entry
        # given they have the attributes set???
        if isinstance(other, BigEntry):
            with self.stream_raw_data() as fp_1:
                with other.stream_raw_data() as fp_2:
                    while True:
                        b1 = fp_1.read(BUFSIZE)
                        b2 = fp_2.read(BUFSIZE)
                        if b1 != b2:
                            return False
                        if not b1:
                            break
        # NotImplemented is not what we want here since it just
        # calls other.__eq__(self) and if it is a big entry it
        # also returns NotImplemented making 'self == other'
        # essentially 'self is other' which isn't what we want!
        return super().__eq__(other)

    def extract_all(self, dirname):
        self.__get_manager().extract_all(self, dirname)

    # Big manager registration
    @classmethod
    def add_manager(cls, name, manager):
        if not isinstance(manager, BigEntryManager):
            raise TypeError(f'manager must be a BigEntryManager, not '
                            f'{manager!r}')
        if name in cls._big_managers:
            raise ValueError(f'big entry manager {name!r} is already '
                             f'registered')
        cls._big_managers[name] = manager

    @classmethod
    def get_manager(cls, name):
        return cls._big_managers[name]

    @classmethod
    def has_manager(cls, name):
        return name in cls._big_managers

    @classmethod
    def remove_manager(cls, name):
        return cls._big_managers.pop(name)

    @classmethod
    def get_manager_names(cls):
        return cls._big_managers.keys()

    # Getters and setters
    # Every attribute has the prefix "big:"... so namespace!  Woohoo!
    def get_main_file(self):
        return self.get_attribute('big:mf_name')

    def set_main_file(self, value):
        self.set_attribute('big:mf_name', os.path.normpath(value))

    def set_type(self, value):
        if not self.has_manager(value):
            raise ValueError(f'unknown archive format: {value!r}')
        super().set_type(value)

    def set_format(self, value):
        if value is not None:
            raise ValueError('big entry does not allow format to be set')
        super().set_format(None)

    def set_encoding(self, value):
        if value != 'binary':
            raise ValueError('big entry does not allow format to be set')
        super().set_encoding('binary')

    # TODO: Implement type checking
    def get_main_file_type(self):
        return self.get_attribute('big:mf_type')

    def set_main_file_type(self, value):
        self.set_attribute('big:mf_type', value)

    def get_main_file_encoding(self):
        return self.get_attribute('big:mf_enc')

    def set_main_file_encoding(self, value):
        self.set_attribute('big:mf_enc', value)

    def get_main_file_format(self):
        return self.get_attribute('big:mf_format')

    def set_main_file_format(self, value):
        self.set_attribute('big:mf_format', value)

    def has_main_file_format(self):
        return self.get_main_file_format() is None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._big_managers = mngmap = {}
        for base in cls.__mro__[:0:-1]:
            if issubclass(base, BigEntry):
                mngmap.update(base._big_managers)


#
# The only difference this loader makes is when an entry dict contains
# a dictionary for 'data'.  In that case, the dictionary must provide
#
#   *  precisely one of 'raw' (paired with 'data-encoding') and 'input'; and
#   *  the path of the main file within the archive, through 'main-file'.
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
#         "date-time": "2021-12-17 12:00",
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
# The inference rules will work as expected!  (I hope...)
# So if 'main-file' is 'main.md', then you can expect the main file
# type to be 'markdown'.
#
class BigLoader(JSONLoader):
    __slots__ = ()

    def get_entry_extensions(self, entry, panel, attrs):
        extensions = super().get_entry_extensions(entry, panel, attrs)
        if 'data' in entry and isinstance(entry['data'], dict):
            extensions.append(BigEntry)
        return extensions

    def make_entry(self, entry_class, entry, panel, attrs):
        if not issubclass(entry_class, BigEntry):
            return super().make_entry(entry_class, entry, panel, attrs)

        im = self.get_inference_manager()
        arc_data = entry.pop('data').copy()
        # Raise exception for extraneous keys
        for k in ('input', 'type', 'encoding'):
            if k in entry:
                raise ValueError(f'invalid key for big entry: {k!r}')
        for k in ('data', 'data-encoding'):
            if k in arc_data:
                raise ValueError(f'invalid key for archive data: {k!r}')

        # Get the important things: archive format and main file path,
        # also transfer the raw data/source path to 'entry' so we can use
        # the super process_entry() to parse the entry normally.
        main_file = arc_data.pop('main-file')
        arc_format = entry.pop('format', None)
        if 'input' in arc_data and 'raw' in arc_data:
            raise ValueError('exactly one of input and raw can be '
                             'specified in archive data')
        if 'input' in arc_data:
            arc_path = entry['input'] = arc_data.pop('input')
            if arc_format is None:
                arc_format = im.infer_type_from_path(arc_path)
        elif 'raw' in arc_data:
            entry['data'] = arc_data.pop('raw')
            entry['data-encoding'] = arc_data.pop('data-encoding')

        if arc_format is None:
            raise ValueError('unable to infer archive format; '
                             'must be explicitly specified')

        entry['type'] = arc_format
        entry['encoding'] = 'binary'

        obj = super().make_entry(entry_class, entry, panel, attrs)

        # Extracting type, encoding and format from archive data
        if 'type-format' in arc_data:
            mf_type, mf_format = arc_data.pop('type-format').split('-', 1)
        else:
            mf_type = arc_data.pop('type', None)
            mf_format = arc_data.pop('format', None)

        # Inference
        mf_enc = arc_data.pop('encoding', 'utf-8')
        if mf_type is None:
            mf_type = im.infer_type_from_path(main_file)
        if mf_type is None:
            mf_type = im.infer_type_from_encoding(mf_enc)
            if mf_type is None:
                mf_type = 'plain'
        if mf_enc is None:
            mf_enc = im.infer_encoding_from_type(mf_type)
            if mf_enc is None:
                mf_enc = 'utf-8'
            elif mf_enc == 'binary':
                raise ValueError(f'inferred a non-text encoding for '
                                 f'{mf_type!r}')

        if mf_enc == 'binary':
            raise ValueError('encoding must not be binary (main file '
                             'should be a text file)')

        obj.set_main_file(main_file)
        obj.set_main_file_type(mf_type)
        obj.set_main_file_encoding(mf_enc)
        obj.set_main_file_format(mf_format)

        if arc_data:
            remaining = ', '.join(sorted(map(str, arc_data.keys())))
            self._warn(f'ignored archive data keys: {remaining}',
                       RuntimeWarning)
        return obj


class BigDumper(JSONDumper):
    __slots__ = ()

    def get_input_path(self, entry, attrs):
        if not isinstance(entry, BigEntry):
            return super().get_input_path(entry, attrs)
        base = self.get_export_path_name(entry)
        ext = self.get_export_path_extension(entry)
        filename = self.generate_export_path(base, ext, 'doc')
        self.export_entry(entry, os.path.join('doc', filename))
        return self.compute_input_path(filename, 'doc')

    def use_inline_text(self, entry):
        if isinstance(entry, BigEntry):
            return False
        return super().use_inline_text(entry)

    def wrap_entry(self, entry, attrs):
        entry_dict = super().wrap_entry(entry, attrs)
        if isinstance(entry, BigEntry):
            # archive format
            assert entry_dict.pop('format', None) is None
            if 'type' in entry_dict:
                entry_dict['format'] = entry_dict.pop('type')
            if 'encoding' in entry_dict:
                assert entry_dict.pop('encoding') == 'binary'

            # big entry data: one of 'raw' and 'input'
            if 'data' in entry_dict:
                entry_dict['raw'] = entry_dict.pop('data')
            data_dict = entry_dict['data'] = {
                k: entry_dict.pop(k) for k in
                ('input', 'raw', 'data-encoding')
                if k in entry_dict}

            # main file
            mf_name = entry.get_main_file()
            mf_type = entry.get_main_file_type()
            mf_enc = entry.get_main_file_encoding()
            mf_format = entry.get_main_file_format()
            im = self.get_inference_manager()

            data_dict['main-file'] = mf_name
            i_type = im.infer_type_from_path(mf_name)
            i_enc = im.infer_encoding_from_type(mf_type)
            if i_enc is None:
                i_enc = 'utf-8'
            if i_type is not None:
                if i_type != mf_type:
                    self.write_entry_type_and_format(
                        data_dict, mf_type, mf_format)
                elif mf_format is not None:
                    data_dict['format'] = mf_format
                if i_enc != mf_enc:
                    data_dict['encoding'] = mf_enc
            else:
                # neither type nor encoding
                i_type = im.infer_type_from_encoding('utf-8')
                if i_type is None:
                    i_type = 'plain'
                if i_type == mf_type and i_enc == mf_enc:
                    if mf_format is not None:
                        data_dict['format'] = mf_format
                else:
                    # only encoding
                    i_type = im.infer_type_from_encoding(mf_enc)
                    if i_type is None:
                        i_type = 'plain'
                    if i_type == mf_type:
                        data_dict['encoding'] = mf_enc
                        if mf_format is not None:
                            data_dict['format'] = mf_format
                    else:
                        # type, optionally w/ encoding
                        self.write_entry_type_and_format(
                            data_dict, mf_type, mf_format)
                        if i_enc != mf_enc:
                            data_dict['encoding'] = mf_enc

        return entry_dict


# Default big entry to make everyone's lives easier! :D


class ArchiveManager(BigEntryManager):
    def extract_all(self, entry, dirpath):
        if entry.has_source():
            self.__extract(entry.get_source(), dirpath)
        else:
            fp = tempfile.NamedTemporaryFile(delete=False)
            try:
                with fp:
                    with entry.stream_raw_data() as fsrc:
                        shutil.copyfileobj(fsrc, fp)
                self.__extract(fp.name)
            finally:
                os.unlink(fp.name)

    def __extract(self, arcpath, dirpath):
        shutil.unpack_archive(arcpath, dirpath, self.arc_format)

    def stream_main_file_data(self, entry):
        mf_name = os.path.normpath(entry.get_main_file())
        mf_enc = entry.get_main_file_encoding()
        if entry.has_source():
            return self.stream_mfdata(entry.get_source(), mf_name, mf_enc)
        fp = tempfile.NamedTemporaryFile(delete=False)
        try:
            with fp:
                with entry.stream_raw_data() as fsrc:
                    shutil.copyfileobj(fsrc, fp)
            return self.stream_mfdata(fp.name, mf_name, mf_enc)
        finally:
            os.unlink(fp.name)

    def get_main_file_data(self, entry):
        with self.stream_main_file_data(entry) as fp:
            return fp.read()


# XXX: How do these decorators make any sense??? :DD
@staticmethod
@contextmanager
def stream_zip_mfdata(filename, mf_name, mf_enc):
    with zipfile.ZipFile(filename) as zf:
        for name in zf.namelist():
            if os.path.normpath(name) == mf_name:
                with zf.open(name) as mainfp:
                    yield io.TextIOWrapper(mainfp, encoding=mf_enc)
                    return
    raise ValueError(f'cannot find main file {filename!r}')


@staticmethod
@contextmanager
def stream_tar_mfdata(filename, mf_name, mf_enc):
    with tarfile.open(filename) as tf:
        for member in tf.getmembers():
            if os.path.normpath(member.name) == mf_name:
                with tf.extractfile(member) as mainfp:
                    yield io.TextIOWrapper(mainfp, encoding=mf_enc)
                    return
    raise ValueError(f'cannot find main file {filename!r}')


# formats that shutil.unpack_archive() can unpack
supported_formats = [fmt for (fmt, _, _) in shutil.get_unpack_formats()]
if 'zip' in supported_formats:
    class ZipManager(ArchiveManager):
        arc_format = 'zip'
        stream_mfdata = stream_zip_mfdata

    BigEntry.add_manager('zip', ZipManager())
    del ZipManager

if 'tar' in supported_formats:
    class TarManager(ArchiveManager):
        arc_format = 'tar'
        stream_mfdata = stream_tar_mfdata

    BigEntry.add_manager('tar', TarManager())
    del TarManager

if 'gztar' in supported_formats:
    class GzTarManager(ArchiveManager):
        arc_format = 'gztar'
        stream_mfdata = stream_tar_mfdata

    BigEntry.add_manager('gztar', GzTarManager())
    del GzTarManager

if 'bztar' in supported_formats:
    class BzTarManager(ArchiveManager):
        arc_format = 'bztar'
        stream_mfdata = stream_tar_mfdata

    BigEntry.add_manager('bztar', BzTarManager())
    del BzTarManager

if 'xztar' in supported_formats:
    class XzTarManager(ArchiveManager):
        arc_format = 'xztar'
        stream_mfdata = stream_tar_mfdata

    BigEntry.add_manager('xztar', XzTarManager())
    del XzTarManager

del supported_formats
del stream_zip_mfdata, stream_tar_mfdata
del ArchiveManager
