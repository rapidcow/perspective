"""Random utility functions"""
import itertools
from . import Panel
from . import timeutil

__all__ = ['merge_panels', 'panels_equal', 'entries_equal']

def merge_panels(panels):
    """Merge a list of panels and return one panel."""
    if len(panels) == 1:
        return panels[0]
    for p1, p2 in itertools.combinations(panels, 2):
        if p1.date != p2.date:
            raise ValueError(f"{len(panels)} panels don't have the "
                             f"same date")
        if p1.get_attribute_dict() != p2.get_attribute_dict():
            raise ValueError(f"{len(panels)} panels on {panels[0].date} "
                             f"don't agree in attributes")
    sample_panel = panels[0]
    new_panel = Panel(sample_panel.date)
    for attr, value in sample_panel.get_attribute_dict().items():
        new_panel.set_attribute(attr, value)
    for p in panels:
        # Need to make a copy of the entry list!
        for e in p.get_entries():
            new_panel.add_entry(e)
    return new_panel


def _entry_utc_time(entry):
    return timeutil.to_utc(entry.date_time)


def panels_equal(panel1, panel2):
    """Determine if two panels are equal"""
    assert panel1.date == panel2.date
    if panel1.get_attribute_dict() != panel2.get_attribute_dict():
        return False
    if panel1.count() != panel2.count():
        return False
    return all(map(entries_equal,
                   sorted(panel1.entries(), key=_entry_utc_time),
                   sorted(panel2.entries(), key=_entry_utc_time)))


def entries_equal(entry1, entry2):
    """Determine if two entries are equal"""
    if timeutil.to_utc(entry1.date_time) != timeutil.to_utc(entry2.date_time):
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
