import unittest


class TestImport(unittest.TestCase):
    def test_import(self):
        import genpsp
        self.assertEqual(genpsp.__version__, '0.0.0')


if __name__ == '__main__':
    unittest.main()
