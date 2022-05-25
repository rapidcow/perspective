"""Random utility functions"""
import itertools
from . import Panel

__all__ = [
    'merge_panels', 'panels_equal', 'entries_equal',
    'checksum',
]


def merge_panels(panels):
    """Merge a list of panels and return one panel."""
    if len(panels) == 1:
        return panels[0]
    sample_panel = panels[0]
    merged_panel = Panel(sample_panel.date)
    for attr, value in sample_panel.get_attribute_dict().items():
        merged_panel.set_attribute(attr, value)
    for p in panels:
        # Need to make a copy of the entry list!
        for e in p.get_entries():
            merged_panel.add_entry(e)
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
    for entries in entry_list:
        panel_count += 1
        for entry in entries:
            entry_count += 1
            size += entry.get_raw_data_size()
    return (panel_count, entry_count, size)
