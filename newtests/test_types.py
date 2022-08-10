"""Test the psp.types module."""
from datetime import date, datetime, timezone
import unittest
from psp.types import Panel, Entry, Configurable


class TestPanel(unittest.TestCase):
    # TODO: Help i'm procrastinating QnQ
    # TEST 1
    # ------
    def test_initialization(self):
        with self.assertRaises(TypeError):
            Panel(date=date(2022, 2, 2))
        with self.assertRaises(TypeError):
            Panel()
        with self.assertRaises(TypeError):
            Panel(date(2022, 2, 2), sus=True)

    # TEST 2
    # ------
    def test_repr(self):
        pass

    # TEST 3
    # ------
    def test_entry_modification(self):
        """Test the add_entry, remove_entry(), and has_entry() methods of
        Panel and the panel attribute and the has_panel() method of Entry.
        """
        utc = timezone.utc

        #
        # 1. add_panel(entry) adds if entry is not already added;
        #    ValueError otherwise.
        #
        p1 = Panel(date(2022, 1, 1))
        # To address the edge case in problem 1, we'll use two entries that
        # compare equal...
        e1 = Entry(datetime(2022, 1, 1, tzinfo=utc))
        e2 = e1.copy()
        self.assertEqual(e1, e2)
        self.assertIsNot(e1, e2)

        p1.add_entry(e1)
        self._check_panel_entries(p1, [e1])
        p1.add_entry(e2)
        self._check_panel_entries(p1, [e1, e2])
        with self.assertRaises(ValueError):
            p1.add_entry(e1)
        with self.assertRaises(ValueError):
            p1.add_entry(e2)

        #
        # 2. remove_entry(entry) removes an entry if it is in panel
        #    (in terms IDENTITY, not EQUALITY); ValueError otherwise.
        #
        p1.remove_entry(e2)
        self._check_panel_entries(p1, [e1])
        with self.assertRaises(ValueError):
            p1.remove_entry(e2)

        #
        # 3. If add_entry() is called with an entry already added to a
        #    different panel, remove_entry() of that panel is called to
        #    prior to adding.
        #
        p1 = Panel(date(2022, 1, 1))
        p2 = Panel(date(2021, 12, 31))
        e1 = Entry(datetime(2022, 1, 2, tzinfo=utc))

        p1.add_entry(e1)
        self._check_panel_entries(p1, [e1])
        self._check_panel_entries(p2, [])
        p2.add_entry(e1)
        self._check_panel_entries(p1, [])
        self._check_panel_entries(p2, [e1])

        # 4. self.has_entry(entry) should be equiv. to entry.panel is self
        p1.add_entry(e1)
        self.assertTrue(p1.has_entry(e1))
        self.assertFalse(p2.has_entry(e1))
        self.assertIs(e1.panel, p1)

        p2.add_entry(e1)
        self.assertTrue(p2.has_entry(e1))
        self.assertFalse(p1.has_entry(e1))
        self.assertIs(e1.panel, p2)

    def _check_panel_entries(self, panel, expected):
        entries = panel.get_entries()
        self.assertListEqual(entries, expected)
        # no hooman index today o-o
        for i, (e1, e2) in enumerate(zip(entries, expected)):
            self.assertIs(e1, e2, msg=f'item {i}')
