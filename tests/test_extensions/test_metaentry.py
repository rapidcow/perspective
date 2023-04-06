import unittest
from psp.ext import metadata


class TestMetaEntry(unittest.TestCase):
    metadata.MetaEntry


class TestMetaJSONLoader(unittest.TestCase):
    metadata.MetaJSONLoader


class TestMetaJSONDumper(unittest.TestCase):
    metadata.MetaJSONDumper
