"""Test the psp.datatypes module."""

import unittest
from psp import datatypes


class TestRegistration(unittest.TestCase):
    pass


class TestLookup(unittest.TestCase):
    """General lookup functions."""
    def test_is_text_type(self):
        self.assertIs(datatypes.is_text_type('binary'), False)
        self.assertIs(datatypes.is_text_type('plain'), True)
        self.assertIs(datatypes.is_text_type('markdown'), True)
        with self.assertRaises(LookupError, msg='among us'):
            datatypes.is_text_type('among us')

    def test_path_to_type(self):
        self.assertEqual(datatypes.path_to_type('test.jpeg'), 'jpeg')
        self.assertEqual(datatypes.path_to_type('a.tar.gz'), 'gztar')
