"""Data types inference rules for their names, file extension, etc."""

from collections import namedtuple, deque
from functools import lru_cache as _cache
import itertools
import os

__all__ = [
    # Membership check
    'has_type', 'has_extension', 'has_alias',
    # Listing stuff
    'list_types', 'list_extensions', 'list_aliases',
    # Lookup
    'is_text_type', 'get_extension', 'get_aliases',
    # Reverse lookup
    'path_to_type', 'alias_check',
    # New type registeration
    'register_data_type', 'delete_data_type',
    # Cache
    'clear_cache',
]


class dtype(namedtuple('dtype', ['is_text', 'exts', 'aliases'])):
    __slots__ = ()

    def __new__(cls, is_text, exts=(), aliases=()):
        if not isinstance(is_text, bool):
            raise TypeError(f'is_text should be a bool, not {is_text!r}')
        if not isinstance(exts, (list, tuple)):
            raise TypeError(f'exts should be a list or tuple, not {exts!r}')
        exts = tuple(exts)
        if not isinstance(aliases, (list, tuple)):
            raise TypeError(f'aliases should be a list or tuple, not '
                            f'{aliases!r}')
        aliases = tuple(aliases)
        for i, ext in enumerate(exts, start=1):
            if not isinstance(ext, str):
                raise TypeError(f'item {i} of exts is not str: {ext!r}')
        for i, alias in enumerate(aliases, start=1):
            if not isinstance(alias, str):
                raise TypeError(f'item {i} of aliases is not str: {alias!r}')
        return super().__new__(cls, is_text, exts, aliases)


# Internal storage:
#   [name, is text, extensions, aliases]
_types = {
    # General text
    'plain': dtype(True, ('.txt',), ()),
    # General binary
    'binary': dtype(False, (), ()),
    # I love these
    'markdown': dtype(True, ('.md', '.markdown'), ('md',)),
    'html': dtype(True, ('.html',), ()),
    'css':  dtype(True, ('.css',), ()),
    'tex':  dtype(True, ('.tex', '.sty', '.cls', '.dtx'), ()),
    # Okay but why
    'xml':  dtype(True, ('.xml',), ()),
    'json': dtype(True, ('.json',), ()),
    'yaml': dtype(True, ('.yaml', '.yml'), ('yml',)),
    # Archive files
    'zip': dtype(False, ('.zip',), ()),
    'tar': dtype(False, ('.tar',), ()),
    'gztar': dtype(False, ('.tar.gz', '.tgz'), ('targz',)),
    'bztar': dtype(False, ('.tar.bz2', '.tbz'), ('tarbz',)),
    # Compressed files
    'gz': dtype(False, ('.gz',), ()),
    'bz': dtype(False, ('.bz2',), ()),
    # Programming languages
    'python': dtype(True, ('.py',), ()),
    'c':    dtype(True, ('.c',), ()),
    'c++':  dtype(True, ('.cc', '.cpp'), ()),
    'java': dtype(True, ('.java',), ()),
    'javascript': dtype(True, ('.js',), ()),
    'perl': dtype(True, ('.pl',), ()),
    # Image
    'png':  dtype(False, ('.png',), ()),
    'jpeg': dtype(False, ('.jpg', '.jpeg'), ('jpg',)),
    'tiff': dtype(False, ('.tiff',), ()),
    'heic': dtype(False, ('.heic',), ()),
    # Video
    'mp4':  dtype(False, ('.mp4',), ()),
    'mov':  dtype(False, ('.mov',), ()),
    'wmv':  dtype(False, ('.wmv',), ()),
    'avi':  dtype(False, ('.avi',), ()),
    # Audio
    'mp3':  dtype(False, ('.mp3',), ()),
    'flac': dtype(False, ('.flac',), ()),
    'wav':  dtype(False, ('.wav',), ()),
    'm4a':  dtype(False, ('.m4a',), ()),
    'aiff': dtype(False, ('.aiff',), ()),
    'midi': dtype(False, ('.midi',), ()),
    # Document types
    'pdf':  dtype(False, ('.pdf',), ()),
    # Microsoft Office files (since everyone loves them so much...)
    'docx': dtype(False, ('.docx',), ('word', 'word_open_xml')),
    'doc':  dtype(False, ('.doc',),  ('word_binary',)),
    'pptx': dtype(False, ('.pptx',), ('powerpoint',
                                         'powerpoint_open_xml',)),
    'ppt':  dtype(False, ('.ppt',),  ('powerpoint_binary',)),
    'xlsx': dtype(False, ('.xlsx',), ('excel', 'excel_open_xml')),
    'xls':  dtype(False, ('.xls',),  ('excel_binary',)),
    'musescore': dtype(False, ('.mscz',), ('musescore_compressed',)),
    'musescore_uncompressed': dtype(True, ('.mscx',), ()),
    'lilypond': dtype(True, ('.ly',), ()),
    'lilypond-tex': dtype(True, ('.lytex',), ()),
}

# Extension to name (multiple names may have the same name, in which case
# the extension is not considered)
_ext2type = {}

# Alias to name (should be unique; i mean that's the whole point of having
# an alias!)
_alias2name = {}


def _make_conv():
    """Make conversion tables"""
    _ext2type.clear()
    _alias2name.clear()
    ambiguous_ext = set()
    for name, (is_text, exts, aliases) in _types.items():
        for ext in exts:
            if ext not in _ext2type:
                _ext2type[ext] = name
            else:
                ambiguous_ext.add(ext)

        for ext in ambiguous_ext:
            del _ext2type[ext]

        for alias in aliases:
            if alias not in _alias2name:
                _alias2name[alias] = name
            else:
                raise ValueError(f'duplicate alias: {alias!r}')
            if alias in _ext2type:
                raise ValueError(f'alias {alias!r} is already a type name')


_make_conv()
_NoValue = object()


def has_type(name):
    return name in _types


def path_to_type(path, *, default=_NoValue):
    try:
        return _path_to_type(path)
    except LookupError:
        if default is _NoValue:
            raise
    return default


def _path_to_type(path):
    parts = os.path.basename(path).split('.')
    # The part after the leading dot is not an extension
    if parts and not parts[0]:
        parts.pop(0)
    # Strip out the file name part.  The rest are all going to be tested
    # for extension.
    parts = deque(parts[1:])

    while parts:
        try:
            return _ext2type['.' + '.'.join(parts)]
        except KeyError:
            pass
        parts.popleft()
    raise LookupError(path)


def get_extensions(name):
    """Get extensions for data type with the name 'name'.
    LookupError is raised if the name is not registered.
    """
    return _types[name].exts


def get_extension(name, *, default=_NoValue):
    """Get the first extension of the extension list associated
    with the type 'name'.  LookupError is raised when default is
    not provided and either 'name' is not registered or no extensions
    exist are associated with this type.
    """
    try:
        exts = _types[name].exts
    except KeyError:
        if default is _NoValue:
            raise
        return default
    if not exts:
        if default is _NoValue:
            raise LookupError(f'no extensions are associated with the type '
                              f'{name!r}')
        return default
    return exts[0]


@_cache()
def has_extension(ext):
    try:
        _path_to_type('a' + ext)
    except LookupError:
        return False
    return True


def is_text_type(name, *, default=_NoValue):
    try:
        return _types[name].is_text
    except LookupError:
        if default is _NoValue:
            raise
    return default


def get_aliases(name, *, default=_NoValue):
    try:
        return _types[name].aliases
    except LookupError:
        if default is _NoValue:
            raise
    return default


def alias_check(name):
    if name in _alias2name:
        return _alias2name[name]
    return name


def has_alias(alias):
    return alias in _alias2name


def register_data_type(name, type_tuple):
    if name in _types:
        raise ValueError(f'{name!r} has already been registered')
    t = dtype(type_tuple)
    exts = tuple(exts)
    for ext in exts:
        if '.' not in ext:
            raise ValueError(f'extension {ext!r} has no dot')
    for alias in aliases:
        if alias in _alias2name:
            raise ValueError(f'alias {alias!r} is already an alias of '
                             f'{alias_check(alias)}')
        if alias in _types:
            raise ValueError(f'alias {alias!r} is a registered type name')

    _types[name] = t
    for ext in exts:
        _ext2type[ext] = name
    for alias in aliases:
        _alias2name[alias] = name
    clear_cache()


def delete_data_type(name):
    try:
        t = _types.pop(name)
    except KeyError:
        raise ValueError(f'{name!r} is not registered') from None
    try:
        _make_conv()
        clear_cache()
    except:
        # XXXXX: Is this really good???
        _types[name] = t
        raise
    return t


def clear_cache():
    """Clear all cache of function wrappers in this module."""
    has_extension.cache_clear()


def list_types():
    """Return a list of all registered type names."""
    # I know i don't have to write .keys() for those who might ask...
    # but i prefer to be explicit here. :)
    return list(_types.keys())


def list_extensions():
    """Return a list of all (not necessaily unique) registered file
    extensions.
    """
    values = (t.exts for t in _types.values())
    return list(itertools.chain.from_iterable(values))


def list_aliases():
    """Return a list of all registered type aliases."""
    values = (t.aliases for t in _types.values())
    return list(itertools.chain.from_iterable(values))
