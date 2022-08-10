"""Thread-local context for file types."""
from collections import defaultdict
import contextlib
import contextvars
import copy

from .types import _assert_type

__all__ = [
    'get_context', 'set_context', 'local_context',
    'FileTypeContext',
]

_context_var = contextvars.ContextVar('psp_filetypes_context')


def get_context():
    try:
        return _context_var.get()
    except LookupError:
        context = FileTypeContext()
        _context_var.set(context)
        return context


def set_context(context):
    _context_var.set(context)


@contextlib.contextmanager
def local_context(context=None):
    if context is None:
        context = FileTypeContext()
    else:
        context = context.copy()
    token = _context_var.set(context)
    try:
        yield context
    finally:
        _context_var.reset(token)


def _assert_is_iterable_of_str(obj, name):
    for i, item in enumerate(obj, start=1):  # hooman index
        if isinstance(item, str):
            continue
        raise TypeError(f'{name!r} should be an iterable of str, '
                        f'but found item {i} to be {item!r}')


class FileTypeContext:
    __slots__ = ('_type_reg', '_type_to_exts', '_ext_reg', '_alias_reg')

    def __init__(self):
        self._type_reg = {}
        self._type_to_exts = defaultdict(list)
        self._ext_reg = {}
        self._alias_reg = {}
        self.add_type('plain', True, ('.txt',))
        self.add_type('binary', False)

    def copy(self):
        # XXX: Does this work?
        return copy.deepcopy(self)

    # registration
    def add_type(self, name, /, is_text, exts=None, aliases=None):
        exts = list(exts) if exts else []
        aliases = list(aliases) if aliases else []
        _assert_type(name, str, 'name')
        _assert_type(is_text, bool, 'is_text')
        _assert_is_iterable_of_str(exts, 'exts')
        _assert_is_iterable_of_str(aliases, 'exts')
        if self.has_type(name):
            raise ValueError(f'file type {name!r} has already been '
                             f'registered')
        for ext in exts:
            if self.has_extension(ext):
                raise ValueError(f'extension {ext!r} has already been '
                                 f'registered')
        for alias in aliases:
            if self.has_alias(alias):
                raise ValueError(f'alias {alias!r} has already been '
                                 f'registered')
        self._type_reg[name] = is_text
        if exts:
            for ext in exts:
                self._type_to_exts[name].append(ext)
                self._ext_reg[ext] = name
        for alias in aliases:
            self._alias_reg[alias] = name

    def add_extension(self, ext, name, /):
        _assert_type(ext, str, 'ext')
        _assert_type(name, str, 'name')
        if not self.has_type(name):
            raise ValueError(f'file type {name!r} is not registered')
        if self.has_extension(ext):
            raise ValueError(f'extension {ext!r} has already been '
                             f'registered')
        self._type_to_exts[name].append(ext)
        self._ext_reg[ext] = name

    def set_default_extension(self, name, ext, /):
        _assert_type(name, str, 'name')
        _assert_type(ext, str, 'ext')
        if not self.has_type(name):
            raise ValueError(f'file type {name!r} is not registered')
        if self.has_extension(ext):
            reg_name = self.extension_to_type(ext)
            if name != reg_name:
                raise ValueError(f'cannot set default extension for '
                                 f'{name!r} to {ext!r} as it is registered '
                                 f'as an extension for {reg_name!r}')
            self._type_to_exts[name].remove(ext)
        else:
            self._ext_reg[ext] = name
        self._type_to_exts[name].insert(0, ext)

    def add_alias(self, alias, name, /):
        _assert_type(alias, str, 'alias')
        _assert_type(name, str, 'name')
        if not self.has_type(name):
            raise ValueError(f'file type {name!r} is not registered')
        if self.has_type(alias):
            raise ValueError(f'alias {alias!r} is registered as a file type')
        if self.has_alias(alias):
            raise ValueError(f'alias {alias!r} is already registered')
        self._alias_reg[alias] = name

    # also removes extensions and aliases
    def remove_type(self, name, /):
        # name -> (is_text, exts, aliases)
        if not self.has_type(name):
            raise ValueError(f'file type {name!r} is not registered')
        is_text = self._type_reg.pop()
        try:
            exts = self._type_to_exts.pop()
        except KeyError:
            pass
        else:
            for ext in exts:
                self._ext_reg.pop(ext)
        aliases = [
            alias for alias, type_name in self._alias_reg.items()
            if type_name == name
        ]
        for alias in aliases:
            self._alias_reg.pop(alias)
        return is_text, exts, aliases

    # these never remove the type itself
    def remove_extension(self, ext, /):
        try:
            name = self._ext_reg.pop(ext)
        except KeyError:
            raise ValueError(f'extension {ext!r} is not '
                             f'registered') from None
        self._type_to_exts.remove(ext)
        return name

    def remove_alias(self, alias, /):
        try:
            return self._alias_reg.pop(alias)
        except KeyError:
            raise ValueError(f'alias {alias!r} is not '
                             f'registered') from None

    # membership check
    def has_type(self, name, /):
        return name in self._type_reg

    def has_extension(self, extension, /):
        return extension in self._ext_reg

    def has_alias(self, alias, /):
        return alias in self._alias_reg

    def is_text_type(self, name, /):
        return self._type_reg[name]

    def extension_to_type(self, extension, /):
        return self._ext_reg[extension]

    def get_default_extension(self, name, /):
        try:
            return self._type_to_exts[name][0]
        except IndexError:
            raise LookupError(name) from None

    # this is still the same tho
    def alias_check(self, name, /):
        try:
            return self._alias_reg[name]
        except KeyError:
            return name

    # this returns (is_text, exts, aliases)
    def get_type(self, name, /):
        try:
            is_text = self._type_reg[name]
        except KeyError:
            raise ValueError(f'file type {name!r} is not '
                             f'registered') from None
        return is_text, self._type_to_exts[name].copy(), [
            alias for alias, type_name in self._alias_reg.items()
            if type_name == name
        ]

    # iteration (i figured these should return iterators now so instead
    # of being called list_* they're just get_*)
    def get_types(self):
        return self._type_reg.keys()

    def get_extensions(self):
        return self._ext_reg.keys()

    def get_aliases(self):
        return self._alias_reg.keys()
