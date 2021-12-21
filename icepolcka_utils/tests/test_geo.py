"""Tests for geo module"""
import unittest
import numpy as np
from icepolcka_utils.geo import get_bin_altitude, get_bin_distance, \
    get_pos_from_dist, get_target_distance


class GeoTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_bin_altitude(self):
        h1 = get_bin_altitude(100, 3)
        h2 = get_bin_altitude(10000, 10, site_alt=500)
        exp_h1 = 5
        exp_h2 = 2242
        self.assertAlmostEqual(h1, exp_h1, places=0)
        self.assertAlmostEqual(h2, exp_h2, places=0)

    def test_get_bin_distance(self):
        s1 = get_bin_distance(100, 3)
        s2 = get_bin_distance(10000, 10, site_alt=500)
        exp_s1 = 100
        exp_s2 = 9845
        self.assertAlmostEqual(s1, exp_s1, places=0)
        self.assertAlmostEqual(s2, exp_s2, places=0)

    def test_get_target_distance(self):
        origin = (11.573550, 48.148021)  # Mira
        target = (11.278901, 48.086721)  # Poldi
        d = get_target_distance(origin, target) / 1000
        self.assertAlmostEqual(d, 22.9, places=1)  # Tested with google maps

    def test_get_pos_from_dist(self):
        site = (11.5661, 48.1524)
        lon1, lat1 = get_pos_from_dist(site, 1000, 0)
        lon2, lat2 = get_pos_from_dist(site, 1000, 180)
        self.assertAlmostEqual(lon1, 11.5661, places=4)
        self.assertAlmostEqual(lat1, 48.1614, places=4)
        self.assertAlmostEqual(lon2, 11.5661, places=4)
        self.assertAlmostEqual(lat2, 48.1434, places=4)


if __name__ == "__main__":
    unittest.main()
