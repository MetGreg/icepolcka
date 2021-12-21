"""Tests for projection module"""
import unittest
import numpy as np

from icepolcka_utils.projection import spherical_to_cart, proj4_to_osr, \
    geo_to_cart, data_to_cart


class ProjectionTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_spherical_to_cart(self):
        site_coords = (11.573550, 48.148021, 500)
        r1 = np.array([10000])
        r2 = np.array([100, 1000])
        az1 = np.array([45])
        az2 = np.array([90, 225])
        elv1 = np.array([5])
        elv2 = np.array([3, 10])
        xyz1, proj1 = spherical_to_cart(r1, az1, elv1, site_coords[:2])
        xyz2, proj2 = spherical_to_cart(r2, az2, elv2, site_coords)

        self.assertEqual(proj1.GetAttrValue("PROJECTION"),
                         "Azimuthal_Equidistant")
        self.assertEqual(proj2.GetAttrValue("PROJECTION"),
                         "Azimuthal_Equidistant")
        self.assertAlmostEqual(xyz1[0, 2], 877, places=0)
        self.assertAlmostEqual(xyz1[0, 1], 7043, places=0)
        self.assertAlmostEqual(xyz1[0, 0], 7043, places=0)
        np.testing.assert_array_almost_equal(xyz2[:, 2], np.array([505, 673]),
                                             decimal=0)
        np.testing.assert_array_almost_equal(xyz2[:, 1], np.array([0, -696]),
                                             decimal=0)
        np.testing.assert_array_almost_equal(xyz2[:, 0], np.array([100, -696]),
                                             decimal=0)

        self.assertRaises(TypeError, spherical_to_cart, r2, az2, 1,
                          site_coords)
        self.assertRaises(AssertionError, spherical_to_cart, r2, az2, elv2[:1],
                          site_coords)
        self.assertRaises(ValueError, spherical_to_cart, r1, az1, elv1,
                          site_coords[:1])

    def proj4_to_osr(self):
        proj_str1 = "+proj=merc + lat_ts=56.5 +ellps=GRS80"
        proj = proj4_to_osr(proj_str1)
        self.assertTrue(proj.GetAttrValue("PROJECTION").startswith("Mercator"))
        self.assertEqual(proj.GetAttrValue("SPHEROID"), "GRS 1980")

    def test_geo_to_cart(self):
        origin = (10, 50)
        coords1 = np.array([10, 50])
        coords2 = np.array([10, 50.1])
        cart1, proj = geo_to_cart(coords1, origin)
        cart2, proj = geo_to_cart(coords2, origin)
        cart2 = np.around(cart2, decimals=-1)
        np.testing.assert_array_equal(cart1, np.array([0, 0]))
        np.testing.assert_array_equal(cart2, np.array([0, 11120]))
        self.assertEqual(proj.GetAttrValue("PROJECTION"),
                         "Azimuthal_Equidistant")

    @staticmethod
    def test_data_to_cart():
        src = np.array([[10, 20, 30], [100, 110, 120]])
        trg = np.array([[5, 15, 15]])
        data = np.array([10, 20])
        data_int, itp = data_to_cart(data, src, trg)
        exp_array = np.array([10])
        np.testing.assert_array_equal(data_int, exp_array)


if __name__ == "__main__":
    unittest.main()
