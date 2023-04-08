"""Test... text serializer"""
import unittest
import psp.serializers.text as text


class TestTextLoader(unittest.TestCase):
    def test_stuff(self):
        loader = text.TextLoader()
        attrs, panels = loader.loads('DATE 2022-08-01')
        self.assertEqual(attrs, {})
        self.assertEqual(list(panels), [{'date': '2022-08-01'}])
