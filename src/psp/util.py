"""Random utility functions"""
import itertools
import shutil
# Circular import!  (But how did this happen???)
# https://stackoverflow.com/a/22210807
from . import types

__all__ = ['merge_panels', 'checksum', 'fileobjequal', 'copyfileobj']


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
