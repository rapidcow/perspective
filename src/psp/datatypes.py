"""Data types inference rules for their names, file extension, etc."""

from functools import lru_cache as _cache

__all__ = [
    # Membership check
    'has_type', 'has_extension', 'has_alias',
    # Lookup
    'get_is_text', 'get_extension', 'get_aliases',
    # Reverse lookup
    'path_to_type', 'alias_check',
    # New type registeration
    'register_data_type', 'delete_data_type',
    # Cache
    'clear_cache',
    # Debug
    'get_datatypes',
]

# Internal storage:
#   [name, is text, extensions, aliases]
_types = [
    # General text
    ('plain', True, ('.txt',), ()),
    # General binary
    ('binary', False, (), ()),
    # I love these
    ('markdown', True, ('.md', '.markdown'), ('md',)),
    ('html', True,  ('.html',), ()),
    ('css',  True,  ('.css',), ()),
    ('tex',  True,  ('.tex', '.sty', '.cls', '.dtx'), ()),
    # Okay but why
    ('xml',  True,  ('.xml',), ()),
    ('json', True,  ('.json',), ()),
    ('yaml', True,  ('.yaml', '.yml'), ('yml',)),
    ('zip',  False, ('.zip',), ()),
    # Programming languages
    ('python', True, ('.py',), ()),
    ('c',    True,  ('.c',), ()),
    ('c++',  True,  ('.cc', '.cpp'), ()),
    ('java', True,  ('.java',), ()),
    ('javascript', True, ('.js',), ()),
    ('perl', True,  ('.pl',), ()),
    # Image
    ('png',  False, ('.png',), ()),
    ('jpeg', False, ('.jpg', '.jpeg'), ('jpg',)),
    ('tiff', False, ('.tiff',), ()),
    ('heic', False, ('.heic',), ()),
    # Video
    ('mp4',  False, ('.mp4',), ()),
    ('mov',  False, ('.mov',), ()),
    ('wmv',  False, ('.wmv',), ()),
    ('avi',  False, ('.avi',), ()),
    # Audio
    ('mp3',  False, ('.mp3',), ()),
    ('flac', False, ('.flac',), ()),
    ('wav',  False, ('.wav',), ()),
    ('m4a',  False, ('.m4a',), ()),
    ('aiff', False, ('.aiff',), ()),
    ('midi', False, ('.midi',), ()),
    # Misc
    ('pdf',  False, ('.pdf',), ()),
    ('musescore', False, ('.mscz',), ('musescore_compressed',)),
    ('musescore_uncompressed', True, ('.mscx',), ()),
]


def _check():
    names = []
    exts_l = []
    aliases_l = []
    for name, _, exts, aliases in _types:
        assert isinstance(name, str)
        assert (isinstance(exts, tuple)
                and all(isinstance(ext, str) for ext in exts))
        assert (isinstance(aliases, tuple)
                and all(isinstance(alias, str) for alias in aliases))
        names.append(name)
        exts_l.extend(exts)
        aliases_l.extend(aliases)
    assert len(set(names)) == len(names), 'duplicate name'
    assert len(set(exts_l)) == len(exts_l), 'duplicate extension'
    assert len(set(aliases_l)) == len(aliases_l), 'duplicate alias'
    assert (len(set(names + aliases_l)) == len(names)
            + len(aliases_l)), 'name and alias overlap'

_check()


@_cache()
def has_type(name):
    for tup in _types:
        if tup[0] == name:
            return True
    return False


def path_to_type(path, default=None):
    try:
        return _path_to_type(path)
    except LookupError:
        if default is None:
            raise
    return default


def _path_to_type(path):
    parts = path.split('.')
    # The part after the leading dot is not an extension
    if parts and not parts[0]:
        parts.pop(0)
    # Strip out the file name part.  The rest are all going to be tested
    # for extension.
    parts = parts[1:]
    parts.reverse()

    extensions = []
    while parts:
        extensions.append(parts.pop())
        try:
            return _ext_to_type('.' + '.'.join(reversed(extensions)))
        except LookupError:
            pass
    raise LookupError(path)


@_cache
def _ext_to_type(ext):
    for name, _, exts, _ in _types:
        for extension in exts:
            if extension == ext:
                return name
    raise LookupError(ext)


def get_extension(name, default=None):
    try:
        return _get_extension(name)
    except LookupError:
        if default is None:
            raise
    return default


@_cache()
def _get_extension(name):
    for type_name, _, exts, _ in _types:
        if type_name == name:
            return exts[0] if exts else ''
    raise LookupError(name)


@_cache()
def has_extension(ext):
    try:
        _path_to_type('a' + ext)
    except LookupError:
        return False
    return True


def get_is_text(name, default=None):
    try:
        return _get_is_text(name)
    except LookupError:
        if default is None:
            raise
    return default


@_cache()
def _get_is_text(name):
    for type_name, is_text, _, _ in _types:
        if type_name == name:
            return is_text
    raise LookupError(name)


def get_aliases(name, default=None):
    try:
        return _get_aliases(name)
    except LookupError:
        if default is None:
            raise
    return default


@_cache
def _get_aliases(name):
    for type_name, _, _, aliases in _types:
        if type_name == name:
            return aliases
    raise LookupError(name)


@_cache()
def alias_check(name):
    for type_name, _, _, aliases in _types:
        if name in aliases:
            return type_name
    return name


@_cache()
def has_alias(alias):
    return alias_check(alias) != alias


def register_data_type(name, is_text, exts, aliases=None):
    # str, bool, list of str, list of str
    if has_type(name):
        raise ValueError(f'{name!r} has already been registered')
    exts = tuple(exts)
    for ext in exts:
        if has_extension(ext):
            raise ValueError(f'extension {ext!r} exists')
        if '.' not in ext:
            raise ValueError(f'extension {ext!r} has no dot')
    if aliases is None:
        aliases = ()
    else:
        aliases = tuple(aliases)
    for alias in aliases:
        if has_alias(alias):
            raise ValueError(f'alias {alias!r} exists')
    _types.append((name, is_text, exts, aliases))
    try:
        _check()
        clear_cache()
    except:
        _types.pop()
        raise


def delete_data_type(name):
    for index, tup in enumerate(_types):
        if tup[0] == name:
            break
    else:
        raise ValueError(f'{name!r} is not registered')
    entry = _types.pop(index)
    try:
        clear_cache()
    except:
        _types.append(entry)
        raise
    return entry


def clear_cache():
    """Clear all cache of function wrappers in this module."""
    for func in (has_type, has_extension, has_alias,
                 _get_is_text, _get_extension, _get_aliases,
                 _ext_to_type, alias_check):
        func.cache_clear()


def get_datatypes():
    """Get a copy of the internal list of datatypes."""
    return _types.copy()
