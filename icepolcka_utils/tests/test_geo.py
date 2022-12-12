"""Tests for geo module"""
import unittest
from icepolcka_utils import geo


class GeoTest(unittest.TestCase):
    """Tests for all functions in the geo module"""

    def test_get_bin_altitude_returns_correct_height(self):
        """Tests if correct height is returned for site_alt equal to 0"""
        height = geo.get_bin_altitude(100, 3)
        exp_h = 5  # Calculated by hand
        self.assertAlmostEqual(height, exp_h, places=0)

    def test_get_bin_altitude_works_with_site_alt(self):
        """Tests if correct height is returned when site_alt is not 0"""
        height = geo.get_bin_altitude(10000, 10, site_alt=500)
        exp_h = 2242  # Calculated by hand
        self.assertAlmostEqual(height, exp_h, places=0)

    def test_get_bin_distance_returns_correct_height(self):
        """Tests if correct distance is returned for site_alt equal to 0"""
        s_arc = geo.get_bin_distance(100, 3)
        exp_s = 100  # Calculated by hand
        self.assertAlmostEqual(s_arc, exp_s, places=0)

    def test_get_bin_distance_works_with_site_alt(self):
        """Tests if correct distance is returned when site_alt is not 0"""
        s_arc = geo.get_bin_distance(10000, 10, site_alt=500)
        exp_s = 9845  # Calculated by hand
        self.assertAlmostEqual(s_arc, exp_s, places=0)

    def test_get_target_distance_calculates_distance_correctly(self):
        """Tests if the calculated distance between Mira-35 and Poldirad is correct"""
        origin = (11.573550, 48.148021)  # Mira-35
        target = (11.278901, 48.086721)  # Poldi
        dist = geo.get_target_distance(origin, target) / 1000
        self.assertAlmostEqual(dist, 22.9, places=1)  # Tested with Google Maps

    def test_get_pos_from_dist_calculates_position_correctly_towards_north(self):
        """Tests if the calculated position is correct when pointing north"""
        site = (11.5661, 48.1524)
        lon, lat = geo.get_pos_from_dist(site, 1000, 0)
        self.assertAlmostEqual(lon, 11.5661, places=4)  # Latitude must not change towards north
        self.assertAlmostEqual(lat, 48.1614, places=4)  # Calculated by hand

    def test_get_pos_from_dist_calculates_position_correctly_towards_south(self):
        """Tests if the calculated position is correct when pointing south"""
        site = (11.5661, 48.1524)
        lon, lat = geo.get_pos_from_dist(site, 1000, 180)
        self.assertAlmostEqual(lon, 11.5661, places=4)  # Longitude must not change towards south
        self.assertAlmostEqual(lat, 48.1434, places=4)  # Calculated by hand


if __name__ == "__main__":
    unittest.main()
