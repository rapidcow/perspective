import unittest
from psp import datatypes


class TestRegistration(unittest.TestCase):
    pass


class TestLookup(unittest.TestCase):
    """General lookup functions."""
    def test_get_is_text(self):
        self.assertIs(datatypes.get_is_text('binary'), False)

    def test_path_to_type(self):
        self.assertEqual(datatypes.path_to_type('test.jpeg'), 'jpeg')
