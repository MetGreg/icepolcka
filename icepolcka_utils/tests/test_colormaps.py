"""Tests for colormaps module"""
import matplotlib
import unittest

from icepolcka_utils.colormaps import get_precip_cmap


class ColormapsTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_precip_cmap(self):
        cmap = get_precip_cmap()
        self.assertTrue(cmap is not None)


if __name__ == "__main__":
    unittest.main()