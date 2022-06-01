"""Random utility functions"""
import itertools
from . import Panel

__all__ = [
    'merge_panels', 'panels_equal', 'entries_equal',
    'checksum',
]


def merge_panels(panels):
    """Merge an iterable of panels and return one panel.

    NOTE: Every panel object will lose all of their entries!
    """
    piter = iter(panels)
    try:
        zeroth_panel = next(piter)
    except StopIteration:
        raise ValueError('panels has no elements') from None
    # We only permit instances of Panel or any subclass of Panel, so the
    # following checks for that.
    if not isinstance(zeroth_panel, Panel):
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


def _entry_time(entry):
    return entry.date_time


def panels_equal(panel1, panel2):
    """Determine if two panels are equal."""
    assert panel1.date == panel2.date
    if panel1.get_attribute_dict() != panel2.get_attribute_dict():
        return False
    if panel1.count() != panel2.count():
        return False
    return all(map(entries_equal,
                   sorted(panel1.entries(), key=_entry_time),
                   sorted(panel2.entries(), key=_entry_time)))


def entries_equal(entry1, entry2):
    """Determine if two entries are equal."""
    if entry1.date_time != entry2.date_time:
        return False
    if entry1.insight != entry2.insight:
        return False
    if entry1.get_attribute_dict() != entry2.get_attribute_dict():
        return False
    # Compare data (but not the encoding or source path)
    # Also binary and text entries are an immediate false since
    # bytes and str are never equal in Python
    if (entry1.get_type() != entry2.get_type()
            or entry1.get_format() != entry2.get_format()
            or entry1.get_data() != entry2.get_data()):
        return False
    # Compare metadata
    if entry1.get_meta_dict() != entry2.get_meta_dict():
        return False
    return True


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
