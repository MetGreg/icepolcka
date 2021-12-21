"""Tests for handles module"""
import os
import shutil
import unittest
import datetime as dt
import numpy as np
import numpy.ma as ma
from icepolcka_utils.utils import load_config, make_folder, vec_to_meteo, \
    meteo_to_math, polar_to_xy, get_mean_angle


class UtilsTest(unittest.TestCase):

    def setUp(self):
        self.mira_data_file = "data" + os.sep + "mira" + os.sep \
                              + "20190715_0000.mmclx"
        self.config = "config" + os.sep + "test_config.yaml"
        self.output_dir = "output" + os.sep + "utils"

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_load_config(self):
        cfg = load_config(self.config)
        exp_date = dt.datetime(2021, 10, 4)
        self.assertEqual(cfg['date'], exp_date)

    def test_make_folder(self):
        folder = make_folder(self.output_dir, mp=8, radar="Poldirad",
                             date=dt.datetime.now(), hm="rain")
        self.assertTrue(os.path.exists(folder))

        # Test existing folder
        folder = make_folder(self.output_dir, mp=8, radar="Poldirad",
                             date=dt.datetime.now(), hm="rain")
        self.assertTrue(os.path.exists(folder))

    def test_vec_to_meteo(self):
        self.assertEqual(vec_to_meteo(1, 1), 45)
        self.assertEqual(vec_to_meteo(1, -1), 135)
        self.assertEqual(vec_to_meteo(-1, -1), 225)
        self.assertEqual(vec_to_meteo(-1, 1), 315)
        self.assertEqual(vec_to_meteo(1, 0), 90)
        self.assertEqual(vec_to_meteo(0, 1), 0)
        self.assertEqual(vec_to_meteo(-1, 0), 270)
        self.assertEqual(vec_to_meteo(0, -1), 180)
        np.testing.assert_array_equal(vec_to_meteo(0, 0).mask, np.array(True))
        np.testing.assert_array_equal(vec_to_meteo(0, 0).data, np.array(90.0))
        self.assertAlmostEqual(vec_to_meteo(1.1, 1.5), 36, 0)
        np.testing.assert_array_almost_equal(
            vec_to_meteo(np.array([3, 0, 4]), np.array([1, 0, 2])),
            ma.masked_array(np.array([72, 0, 63]), mask=[False, True, False]),
            decimal=0
            )

    def test_meteo_to_math(self):
        self.assertEqual(meteo_to_math(0), 90)
        self.assertEqual(meteo_to_math(90), 0)
        self.assertEqual(meteo_to_math(180), 270)
        self.assertEqual(meteo_to_math(270), 180)
        self.assertEqual(meteo_to_math(360), 90)
        np.testing.assert_array_equal(
            meteo_to_math(np.array([0, 1, 2])), np.array([90, 89, 88])
            )
        self.assertRaises(ValueError, meteo_to_math, 361)
        self.assertRaises(ValueError, meteo_to_math, -1)
        self.assertRaises(ValueError, meteo_to_math, np.array([-1, 0, 1]))

    def test_polar_to_xy(self):
        self.assertRaises(ValueError, polar_to_xy, -1, 10)
        self.assertRaises(ValueError, polar_to_xy, 10, -1)
        self.assertRaises(ValueError, polar_to_xy, 10, 361)
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 45), np.array([71, 71]), decimal=0
            )
        np.testing.assert_array_almost_equal(polar_to_xy(0, 0),
                                             np.array([0, 0]))
        np.testing.assert_array_almost_equal(polar_to_xy(0, 10),
                                             np.array([0, 0]))
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 0), np.array([0, 100])
            )
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 90), np.array([100, 0])
            )
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 180), np.array([0, -100])
            )
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 270), np.array([-100, 0])
            )
        np.testing.assert_array_almost_equal(
            polar_to_xy(100, 360), np.array([0, 100])
            )
        np.testing.assert_array_almost_equal(
            polar_to_xy(np.array([100, 200]), np.array([45, 225])),
            np.array([[71, -141], [71, -141]]), decimal=0
            )
        self.assertRaises(
            ValueError, polar_to_xy, np.array([-1, 5]), np.array([0, 1])
            )
        self.assertRaises(
            ValueError, polar_to_xy, np.array([10, 20]), np.array([-5, 10])
            )
        self.assertRaises(
            ValueError, polar_to_xy, np.array([10, 20]), np.array([365, 20])
            )

    def test_get_mean_angle(self):
        mean1 = get_mean_angle(177, 187)
        mean2 = get_mean_angle(355, 6)
        self.assertEqual(mean1, 182)
        self.assertEqual(mean2, 0.5)


if __name__ == "__main__":
    unittest.main()
