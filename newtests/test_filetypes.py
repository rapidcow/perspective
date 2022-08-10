"""Test the psp.filetypes module."""
import unittest
import psp.filetypes as filetypes

class TestFileTypeContext(unittest.TestCase):
    # TEST 1
    # ------
    def test_default_context(self):
        ctx = filetypes.FileTypeContext()
        self.assertEqual(ctx.is_text_type('plain'), True)
        self.assertEqual(ctx.is_text_type('binary'), False)
        self.assertEqual(ctx.get_default_extension('plain'), '.txt')
        with self.assertRaises(LookupError):
            ctx.get_default_extension('binary')
