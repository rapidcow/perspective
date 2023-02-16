"""Random utility functions"""
from datetime import timezone
import itertools
import importlib
import importlib.util
import os
from pprint import pformat
import shutil
import sys
from textwrap import indent

# Prevent circular import: https://stackoverflow.com/a/22210807
from . import types

__all__ = [
    'merge_panels', 'checksum', 'fileobjequal', 'copyfileobj',
    'cmppanels', 'cmpentries',
    'import_module', 'import_module_from_file',
]


def merge_panels(panels):
    """Merge an iterable of panels and return one panel.

    If the iterable only has one panel, return that panel unchanged.
    If the iterable has more than one panel, create a new panel and add
    each entry to the new panel.  THIS WILL REMOVE EVERY ENTRY IN ALL
    PANELS FROM THE ITERABLE.
    """
    piter = iter(panels)
    try:
        zeroth_panel = next(piter)
    except StopIteration:
        raise ValueError('panels has no elements') from None
    # We only permit instances of Panel or any subclass of Panel, so the
    # following checks for that.
    if not isinstance(zeroth_panel, types.Panel):
        raise TypeError(f'first panel {zeroth_panel!r} is not a '
                        f'Panel instance')
    # If there is only one panel, simply return the panel.
    try:
        first_panel = next(piter)
    except StopIteration:
        return zeroth_panel
    # Make a copy of the zeroth panel
    merged_panel = type(zeroth_panel).from_panel(zeroth_panel)
    for panel in itertools.chain((zeroth_panel, first_panel), piter):
        # Need to make a copy of the entry list!
        for entry in panel.get_entries():
            merged_panel.add_entry(entry)
    return merged_panel


def checksum(panels):
    """Return a tuple of (panel_count, entry_count, total_bytes)."""
    panel_count = 0
    entry_count = 0
    size = 0
    for panel in panels:
        for entries in panel.entries():
            panel_count += 1
            for entry in entries:
                entry_count += 1
                size += entry.get_raw_data_size()
    return (panel_count, entry_count, size)



BUFSIZE = 8192

def fileobjequal(fp1, fp2, length=BUFSIZE):
    """Compare two file objects."""
    while True:
        b1 = fp1.read(length)
        b2 = fp2.read(length)
        if b1 != b2:
            return False
        if not b1:
            return True


def copyfileobj(fsrc, fdst, length=BUFSIZE):
    """Copy file object fsrc to file object fdst."""
    shutil.copyfileobj(fsrc, fdst, length)


# Debugging
def cmppanels(p1, p2):
    """(panel1, panel2) -> debugging info"""
    if p1.date != p2.date:
        print(f'comparing panels on {p1.date} and {p2.date}')
    else:
        print(f'comparing panels on {p1.date}')
    a1 = p1.get_attributes_for_comparison()
    a2 = p2.get_attributes_for_comparison()
    if a1 != a2:
        print('  attrs of panel 1:')
        print(indent(pformat(p1.get_attributes()), '    '))
        print('  attrs of panel 2:')
        print(indent(pformat(p2.get_attributes()), '    '))
    else:
        if p1.get_entries() != p2.get_entries():
            indices = [i for i in range(min(p1.count(), p2.count())) 
                       if p1.get_entry(i) != p2.get_entry(i)]
            diff_str = ', '.join(map(str, indices))
            print(f'  entries differ: {diff_str}')
            if p1.count() > p2.count():
                print(f'  extra entries: {p2.count()} and above')
            elif p2.count() > p1.count():
                print(f'  extra entries: {p1.count()} and above')
            print('  (0 denotes the first entry)')
        else:
            print('  no diff!')


def cmpentries(*args):
    """
    (entry1, entry2) -> debugging info
    (panel1, panel2, index) -> debugging info
    """
    if len(args) == 2:
        e1, e2 = args
    elif len(args) == 3:
        p1, p2, i = args
        e1, e2 = p1.get_entry(i), p2.get_entry(i)
    else:
        raise TypeError(f'expected 2 or 3 positional arguments, '
                        f'got {len(args)}')
    u1 = e1.time.astimezone(timezone.utc).replace(tzinfo=None)
    u2 = e2.time.astimezone(timezone.utc).replace(tzinfo=None)
    if u1 != u2:
        print(f'comparing entries at {e1.time} and {e2.time}:')
        print(f'  UTC times differ: {u1} and {u2}')
    elif u1.utcoffset() != u2.utcoffset():
        print(f'comparing entries at {e1.time} or {e2.time} (UTC {u1})')
    else:
        print(f'comparig entries at {e1.time} (UTC {u1})')
    d1 = e1.get_data()
    d2 = e2.get_data()
    if d1 != d2:
        print(f'  data differ: {_format_data(d1)} and {_format_data(d2)}')
    for attr in 'type', 'format', 'encoding':
        v1 = getattr(e1, f'get_{attr}')()
        v2 = getattr(e2, f'get_{attr}')()
        if v1 != v2:
            print(f'  {attr} differ: {v1!r} and {v2!r}')
    a1 = p1.get_attributes_for_comparison()
    a2 = p2.get_attributes_for_comparison()
    if a1 != a2:
        print('  attrs of panel 1:')
        print(indent(pformat(p1.get_attributes()), '    '))
        print('  attrs of panel 2:')
        print(indent(pformat(p2.get_attributes()), '    '))


def _format_data(s):
    return f'<{type(s).__name__} data of length {len(s)}>'


# https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
def import_module_from_file(modname, file):
    # Resolve the file path so that the module's __file__ attribute
    # is absolute
    file = os.path.realpath(file)
    spec = importlib.util.spec_from_file_location(modname, file)
    if spec is None:
        raise RuntimeError(f'failed to load module {modname!r} at {file!r}')
    module = importlib.util.module_from_spec(spec)
    # Put the module's parent directory at the very front in sys.path
    sys.path.insert(0, os.path.dirname(file))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def import_module(modname, *, package=None, root='.'):
    # sys.path hacks except we clean stuff up
    _clean_up_module_namespace(modname)
    root = os.path.realpath(root)
    sys.path.insert(0, root)
    try:
        spec = importlib.util.find_spec(modname, package=package)
        module = importlib.util.module_from_spec(spec)
        absolute_name = (importlib.util.resolve_name(modname, package)
                         if package is not None else modname)
        sys.modules[absolute_name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    # make this name available for use by other Python scripts
    _clean_up_module_namespace(modname)
    return module


def _clean_up_module_namespace(modname):
    if modname in sys.modules:
        del sys.modules[modname]
        prefix = modname + '.'
        for name in list(sys.modules.keys()):
            if name.startswith(prefix):
                del sys.modules[name]
