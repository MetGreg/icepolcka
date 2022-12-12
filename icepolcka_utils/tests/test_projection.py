"""Tests for projection module"""
import unittest
import numpy as np

from icepolcka_utils import projection


class ProjectionTest(unittest.TestCase):
    """Tests for all functions in the projection module"""
    def setUp(self):
        self.r_coord = np.array([100, 1000])
        self.azi = np.array([90, 225])
        self.elv = np.array([3, 10])
        self.site_coords = (11.573550, 48.148021, 500)

    def test_spherical_to_cart_returns_azimuthal_equidistant_projection(self):
        """Tests if the projection that is returned is an azimuthal_equidistant projection"""
        _, proj = projection.spherical_to_cart(self.r_coord, self.azi, self.elv,
                                               self.site_coords[:2])
        self.assertEqual(proj.GetAttrValue("PROJECTION"), "Azimuthal_Equidistant",
                         "Expected Azimuthal_Equidistant projection")

    def test_spherical_to_cart_returns_expected_coords(self):
        """Tests if the projection that is returned is an azimuthal_equidistant projection"""
        # Expected values calculated by hand
        xyz, _ = projection.spherical_to_cart(self.r_coord, self.azi, self.elv, self.site_coords)
        np.testing.assert_array_almost_equal(xyz[:, 2], np.array([505, 673]), decimal=0)
        np.testing.assert_array_almost_equal(xyz[:, 1], np.array([0, -696]), decimal=0)
        np.testing.assert_array_almost_equal(xyz[:, 0], np.array([100, -696]), decimal=0)

    def test_spherical_to_cart_raises_type_error(self):
        """Test if error is raised when input arrays have wrong type"""
        self.assertRaises(TypeError, projection.spherical_to_cart, self.r_coord, self.azi, 1,
                          self.site_coords)

    def test_spherical_to_cart_raises_assertion_error(self):
        """Test if error is raised when input arrays have wrong shape"""
        self.assertRaises(AssertionError, projection.spherical_to_cart, self.r_coord, self.azi,
                          self.elv[:1],
                          self.site_coords)

    def test_spherical_to_cart_raises_values_error(self):
        """Test if error is raised when site_coords have wrong shape"""
        self.assertRaises(ValueError, projection.spherical_to_cart, self.r_coord, self.azi,
                          self.elv, self.site_coords[:1])

    @staticmethod
    def test_geo_to_cart_returns_expected_coordinates():
        """Test if the coordinates are transformed as expected"""
        origin = (10, 50)
        coords = np.array([10, 50.1])
        cart, _ = projection.geo_to_cart(coords, origin)
        cart = np.around(cart, decimals=-1)
        np.testing.assert_array_equal(cart, np.array([0, 11120]))  # Manually calculated

    @staticmethod
    def test_data_to_cart():
        """Test if data_to_cart function returns data as expected for nearest interpolation"""
        src = np.array([[10, 20, 30], [100, 110, 120]])
        trg = np.array([[5, 15, 15]])
        data = np.array([10, 20])
        data_int, _ = projection.data_to_cart(data, src, trg, method="Nearest")
        exp_array = np.array([10])  # Calculated by hand
        np.testing.assert_array_equal(data_int, exp_array)


if __name__ == "__main__":
    unittest.main()
