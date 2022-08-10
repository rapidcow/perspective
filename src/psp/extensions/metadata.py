"""Entries with metadata."""

__all__ = ['MetaEntry', 'MetaJSONLoader', 'MetaJSONDumper']

import copy
import json
from collections import OrderedDict

from psp.processors.json_processor import JSONLoader, JSONDumper
from psp.types import Entry


_NoValue = object()


class MetaEntry(Entry, extname='meta'):
    __slots__ = ()
    _metavars = set()
    _metahooks = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_attribute('meta', {})

    # Registration (the names are long, i know, but this is the best
    # way that clearly distinguishes from the instance methods i can
    # think of...)
    @classmethod
    def register_meta_attribute(cls, name, hook=None):
        if name in cls._metavars:
            raise ValueError(f'meta attribute {name!r} is already '
                             f'registered')
        cls._metavars.add(name)
        if hook is not None:
            cls._metahooks[name] = hook

    @classmethod
    def unregister_meta_attribute(cls, name):
        # set.remove() raises a KeyError upon failure
        cls._metavars.remove(name)
        return cls._metahooks.pop(name, None)

    @classmethod
    def has_registered_meta_attribute(cls, name):
        return name in cls._metavars

    @classmethod
    def get_registered_meta_attributes(cls):
        return cls._metavars.copy()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._metavars = metavars = set()
        cls._metahooks = hooks = {}
        # Traverse the MRO in reversed order, skipping
        # only the current class.
        for base in cls.__mro__[:0:-1]:
            if issubclass(base, MetaEntry):
                metavars.update(base._metavars)
                hooks.update(base._metahooks)

    def get_meta_attribute(self, name, default=_NoValue):
        meta = self.get_attribute('meta')
        return (meta[name] if default is _NoValue
                else meta.get(name, default))

    def set_meta_attribute(self, name, value):
        if type(self).has_registered_meta_attribute(name):
            try:
                checker = type(self)._metahooks[name]
            except KeyError:
                pass
            else:
                value = checker(self, value)
            self.get_attribute('meta')[name] = value
        else:
            raise ValueError(f'invalid meta attribute: {name!r}')

    def delete_meta_attribute(self, name):
        return self.get_attribute('meta').pop(name)

    def has_meta_attribute(self, name):
        return name in self.get_attribute('meta')

    def get_meta_atttribute_names(self):
        return self.get_attribute('meta').keys()

    def get_meta_attribute_items(self):
        return self.get_attribute('meta').items()

    def get_meta_attributes(self):
        return self.get_attribute('meta').copy()

    def set_meta_attributes(self, *args, **kwargs):
        meta_dict = dict(*args, **kwargs)
        for name, value in meta_dict.items():
            self.set_meta_attribute(name, value)


class MetaJSONLoader(JSONLoader):
    def get_entry_extensions(self, entry, panel, attrs):
        extensions = super().get_entry_extensions(entry, panel, attrs)
        if 'meta' in entry:
            extensions.append(MetaEntry)
        return extensions

    def make_entry(self, entry_class, entry, panel, attrs):
        # 'meta' is still an optional key when the MetaEntry extension is
        # loaded, so we don't count lack of 'meta' an error
        if issubclass(entry_class, MetaEntry):
            try:
                meta = entry.pop('meta').copy()
            except KeyError:
                meta = {}
        else:
            meta = None

        obj = super().make_entry(entry_class, entry, panel, attrs)

        if meta is not None:
            self.process_metadata(obj, meta)
        return obj

    def process_metadata(self, entry, meta):
        for name, value in meta.items():
            entry.set_meta_attribute(name, copy.deepcopy(value))


class MetaJSONDumper(JSONDumper):
    __slots__ = ()

    def wrap_entry(self, entry, attrs):
        entry_dict = super().wrap_entry(entry, attrs)
        if isinstance(entry, MetaEntry):
            meta = self.wrap_metadata(entry, attrs)
            if meta is not None:
                entry_dict['meta'] = meta
        return entry_dict

    # TODO: Write documentation about how each item in meta_dict is a
    # REFERENCE to the original value and mutating them WILL change the
    # metadata value themselves! (in contrast to JSONDumper where everything
    # is immutable and lists and dicts are newly constructed every time)
    def wrap_metadata(self, entry, attrs):
        return entry.get_meta_attributes() or None
