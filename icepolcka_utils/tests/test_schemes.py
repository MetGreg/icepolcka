import os
import unittest

import numpy as np
import xarray as xr

from icepolcka_utils import schemes


class MP8Test(unittest.TestCase):

    def test_get_psd_returns_expected_psd(self):
        scheme = schemes.MP8()
        d, qr, qn, = 0.001, 0.1, 10
        exp_psd = 635.13  # Calculated manually
        psd = scheme.get_psd("rain", d, qr, qn)
        self.assertAlmostEqual(psd, exp_psd, places=2)


class MP10Test(unittest.TestCase):

    def test_get_psd_returns_expected_psd(self):
        scheme = schemes.MP10()
        d, qr, qn, = 0.001, 0.1, 10
        exp_psd = 634.53  # Calculated manually
        psd = scheme.get_psd("rain", d, qr, qn)
        self.assertAlmostEqual(psd, exp_psd, places=2)


class MP28Test(unittest.TestCase):

    def test_get_psd_returns_expected_psd(self):
        scheme = schemes.MP28()
        d, qr, qn, = 0.001, 0.1, 10
        exp_psd = 635.13  # Calculated manually
        psd = scheme.get_psd("rain", d, qr, qn)
        self.assertAlmostEqual(psd, exp_psd, places=2)


class MP30Test(unittest.TestCase):

    def setUp(self):
        self.wrfmp = "test_data" + os.sep + "wrf" + os.sep + "wrfmp_d03_2019-05-28_120000"

    def test_get_psd_returns_expected_psd(self):
        wrfmp = xr.open_dataset(self.wrfmp)
        scheme = schemes.MP30()
        ind = np.index_exp[16, :, :]
        thresh = 10**(-7)
        exp_mean = 735174.3  # Calculated manually for first rain bin
        mean_psd = np.nanmean(scheme.get_psd("rain", wrfmp, ind, thresh)[0])
        self.assertAlmostEqual(mean_psd, exp_mean, places=1)


class MP50Test(unittest.TestCase):

    def test_get_psd_returns_expected_psd_when_lam_below_minimum(self):
        scheme = schemes.MP50()
        d, qr, qn = 0.001, 0.1, 10
        exp_psd = 22264968.09  # Calculated manually
        psd = scheme.get_psd("rain", d, qr, qn)
        self.assertAlmostEqual(psd, exp_psd, places=2)

    def test_get_psd_returns_expected_psd_when_lam_above_maximum(self):
        scheme = schemes.MP50()
        d, qr, qn = 0.001, 0.01, 10**10
        exp_psd = 1.18*10**(-29)  # Calculated manually
        psd = scheme.get_psd("rain", d, qr, qn)
        self.assertAlmostEqual(psd, exp_psd, places=1)


class TestSchemes(unittest.TestCase):

    def test_get_diameters_returns_correct_smallest_diameter(self):
        exp_diam = 4*10**(-6)  # Calculated manually
        diam = schemes.get_diameters()[0]
        self.assertAlmostEqual(diam, exp_diam, places=6)

    def test_get_diameters_returns_correct_largest_diameter(self):
        exp_diam = 0.009  # Calculated manually
        diam = schemes.get_diameters()[-1]
        self.assertAlmostEqual(diam, exp_diam, places=3)

    def test_get_diameters_returns_correct_2nd_largest_diameter(self):
        exp_diam = 0.0065  # Calculated manually
        diam = schemes.get_diameters()[-2]
        self.assertAlmostEqual(diam, exp_diam, places=4)


if __name__ == "__main__":
    unittest.main()
