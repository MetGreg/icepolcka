"""Tests for the hiw module"""
import os
import unittest
import datetime as dt

import numpy as np
import xarray as xr

from tests import utils as test_utils

from icepolcka_utils import hiw, utils


class StatsTest(unittest.TestCase):
    """Tests for the Stats class"""

    def setUp(self):
        thresh = {'graupel': [44], 'hail': [44], 'rain': [44], 'hail_graupel': [44]}
        self.db_path = utils.make_folder("db")
        self.tmp = utils.make_folder("tmp")
        self.data_path = "test_data"
        self.cfg = test_utils.create_config(self.data_path, self.db_path)
        self.cfg['output'] = {'HIW': self.tmp}
        self.stats = hiw.Stats(self.cfg, thresh, 16)

    def tearDown(self):
        test_utils.delete_content(self.db_path)
        test_utils.delete_content(self.tmp)

    def test_get_more_stats_calculates_correct_frequency(self):
        """Test if the calculated event frequency is correct"""
        hm_name, dbz = "graupel", 44
        area = np.array([200, 300, 400])
        self.stats.stats['area'][hm_name][dbz] = area
        self.stats.get_more_stats()
        self.assertEqual(self.stats.stats['frequency'][hm_name][dbz], len(area),
                         "Expected frequency stats to equal length of test area list")

    def test_load_stats_loads_area_as_expected(self):
        """Test if the area loaded equals the area that was saved"""
        hm_name, dbz = "graupel", 44
        area = [200, 300, 400]
        area_dict = {'area': {hm_name: {dbz: area}}}
        np.save(self.stats.file_path, area_dict)
        self.stats.load_stats(self.stats.file_path)
        np.testing.assert_allclose(self.stats.stats['area'][hm_name][dbz], area)

    def test_if_mp_is_transformed_correctly(self):
        """Test if a mp string of None is transformed to a real None"""
        thresh = {'graupel': [44]}
        self.cfg['mp'] = "None"
        stats = hiw.Stats(self.cfg, thresh, 16)
        self.assertTrue(stats.cfg['mp'] is None)

    def test_get_stats_raises_error(self):
        """Test if error is raised when calling the method 'get_stats'"""
        self.assertRaises(NotImplementedError, self.stats.get_stats)

    def test_get_hms_raises_error(self):
        """Test if error is raised when calling the method 'get_hms'"""
        self.assertRaises(NotImplementedError, self.stats.get_hms, "key")

    def test_get_hiw_pixels_raises_error(self):
        """Test if error is raised when calling the method 'get_hiw_pixels'"""
        self.assertRaises(NotImplementedError, self.stats.get_hiw_pixels, "hms", "data", "thresh")


class HMCStatsTest(unittest.TestCase):
    """Tests for the HMCStats class"""

    def setUp(self):
        hm_ids = {'graupel': [7, 8], 'hail': [9], 'rain': [1, 2, 10]}
        self.data_path = "test_data" + os.sep
        self.db_path = utils.make_folder("db")
        self.tmp = utils.make_folder("tmp")
        start = dt.datetime(2019, 5, 28, 12, 5)
        end = dt.datetime(2019, 5, 28, 12, 5, 35)  # Time of DWD data files (RG, HMC, tracks)
        start_str = dt.datetime.strftime(start, "%d.%m.%Y %H:%M:%S")
        end_str = dt.datetime.strftime(end, "%d.%m.%Y %H:%M:%S")
        self.cfg = test_utils.create_config(self.data_path, self.db_path, start=start_str,
                                            end=end_str)
        self.cfg['source'] = "DWD"
        self.cfg['output'] = {'HIW': self.tmp}
        self.stats = hiw.HMCStats(self.cfg, hm_ids, "HID")

    def tearDown(self):
        test_utils.delete_content(self.db_path)
        test_utils.delete_content(self.tmp)

    def test_get_stats_finds_no_hail_pixel(self):
        """Test if the length of hail array is 0 for a data file with no hail"""
        self.stats.get_stats()
        hail_events = np.sum(np.array(self.stats.stats['area']['hail'][5]) > 0)
        self.assertEqual(hail_events, 0, "Expected length of 0, because no hail in the data")

    def test_get_stats_finds_graupel_pixel(self):
        """Test if graupel is recognised in the data file"""
        self.stats.get_stats()
        hail_events = np.sum(np.array(self.stats.stats['area']['graupel'][5]) > 0)
        self.assertEqual(hail_events, 1, "Expected length of 1, because one time step with graupel")

    def test_get_stats_calculates_correct_hail_area(self):
        """Test if the hail area calculated by get_stats is zero for data file with no hail"""
        self.stats.get_stats()
        self.assertEqual(sum(self.stats.stats['area']['hail'][5]), 0,
                         "Expected length of 0, because no hail in the data")

    def test_get_stats_calculates_correct_graupel_area(self):
        """Test if the area calculated by get_stats is correct"""
        grid_area = 400**2/1000**2
        self.stats.get_stats()
        # The data file (DWD hmc) has 3 pixel at height 16 that are classified as graupel (ID=8)
        # within the Mira-35 range
        self.assertEqual(sum(self.stats.stats['area']['graupel'][5]), 3*grid_area,
                         "Expected length of 3*grid_ara")

    def test_get_stats_raises_error_when_rg_and_hm_handles_have_different_length(self):
        """Test if an error is raised when the length of the data handles do not match"""
        self.stats.cfg['data']['HMC'] = "random_path"
        self.assertRaises(AssertionError, self.stats.get_stats)

    def test_get_hms_returns_correct_hail_graupel_hms(self):
        """Test if the correct IDs of graupel/hail are returned"""
        hm_ids = {'graupel': [7, 8], 'hail': [9], 'rain': [1, 2, 10]}
        stats = hiw.HMCStats(self.cfg, hm_ids, "HID")
        ids = stats.get_hms("hail_graupel")
        self.assertEqual(ids, hm_ids['graupel'] + hm_ids['hail'], "Expected IDs to equal input "
                                                                  "IDs of graupel and hail")

    def test_get_hms_returns_correct_rain_general(self):
        """Test if the correct IDs of rain are returned"""
        hm_ids = {'graupel': [7, 8], 'hail': [9], 'rain': [1, 2, 10]}
        stats = hiw.HMCStats(self.cfg, hm_ids, "HID")
        ids = stats.get_hms("rain")
        self.assertEqual(ids, hm_ids['rain'], "Expected IDs to equal input IDs of rain")

    def test_get_hiw_pixels_returns_correct_array(self):
        """Test if the hiw pixels are masked as expected"""
        hms = [1]
        data = np.random.rand(17, 360, 360)*10
        thresh = 41
        rg_data = np.random.rand(17, 360, 360)*100
        exp_hiw = np.where((data == hms[0]) & (rg_data > thresh), data, np.nan)[self.stats.height]
        pixel = self.stats.get_hiw_pixels(hms, data, thresh, rg_data)
        np.testing.assert_allclose(pixel, exp_hiw)


class DolanStatsTest(unittest.TestCase):
    """Test of DolanStats class"""

    def setUp(self):
        self.data_path = "test_data" + os.sep
        self.tmp = "tmp"
        self.db_path = utils.make_folder("db")
        self.cfg = test_utils.create_config(self.data_path, self.db_path)
        self.cfg['output'] = {'HIW': self.tmp}

    def tearDown(self):
        test_utils.delete_content(self.db_path)
        test_utils.delete_content(self.tmp)

    def test_init_creates_correct_hail_id(self):
        """Test if the object initialization is done correctly by checking hail attribute ID"""
        stats = hiw.DolanStats(self.cfg)
        self.assertEqual(stats.hm_ids['hail'][0], 9, "Expected hail ID of 9")


class WRFStatsTest(unittest.TestCase):
    """Tests of WRFStats class"""

    def setUp(self):
        self.data_path = "test_data" + os.sep
        self.db_path = utils.make_folder("db")
        self.tmp = "tmp"
        start = dt.datetime(2019, 5, 28, 12)  # Time of WRF and tracks data
        end = dt.datetime(2019, 5, 28, 13)
        start_str = dt.datetime.strftime(start, "%d.%m.%Y %H:%M:%S")
        end_str = dt.datetime.strftime(end, "%d.%m.%Y %H:%M:%S")
        self.cfg = test_utils.create_config(self.data_path, self.db_path, start=start_str,
                                            end=end_str)
        self.cfg['output'] = {'HIW': self.tmp}
        self.cfg['mp'] = 30
        self.stats = hiw.WRFStats(self.cfg)

    def tearDown(self):
        test_utils.delete_content(self.db_path)
        test_utils.delete_content(self.tmp)

    def test_get_stats_calculates_graupel_area_correctly(self):
        """Test if the calculated graupel area is correct"""
        grid_area = 400**2/1000**2
        self.stats.get_stats()
        # There are 66 pixels at height 7 above 0.0001 g/kg in graupel mixing ratio
        self.assertEqual(sum(self.stats.stats['area']['graupel'][0.0001]),
                         grid_area*66, "Expected the sum of the area entries to equal grid_area*66")

    def test_get_hms_returns_correct_hms(self):
        """Test if the get_hms method returns the correct hm string"""
        hm_name = "graupel"
        hm_out = self.stats.get_hms(hm_name)
        self.assertEqual(hm_name, hm_out, "Expected output hm to equal input hm")

    def test_get_hiw_pixels_returns_correct_array(self):
        """Test if the get_hiw_pixels masks the array as expected"""
        hm_name = "graupel"
        thresh = 2
        data_array = np.random.rand(1, 30, 360, 360)*100
        mask = np.load(self.cfg['masks']['Distance'])
        data_masked = np.where(~mask, data_array[0][self.stats.height], np.nan)
        hiw_exp = np.where(data_masked > thresh, data_masked, np.nan)
        data = xr.Dataset({'QGRAUP': (['time', 'height', 'lon', 'lat'], data_array)})
        hiw_out = self.stats.get_hiw_pixels(hm_name, data, thresh)
        np.testing.assert_allclose(hiw_exp, hiw_out)

    def test_get_hiw_pixels_returns_correct_array_for_p3(self):
        """Test if the get_hiw_pixels masks the array as expected for the p3 scheme"""
        hm_name = "graupel"
        thresh = 2
        data_array = np.random.rand(1, 30, 360, 360)*100
        mask = np.load(self.cfg['masks']['Distance'])
        self.stats.cfg['mp'] = 50
        data_masked = np.where(~mask, data_array[0][self.stats.height], np.nan)
        hiw_exp = np.where(data_masked > thresh, data_masked, np.nan)
        data = xr.Dataset({'QIR': (['time', 'height', 'lon', 'lat'], data_array)})
        hiw_out = self.stats.get_hiw_pixels(hm_name, data, thresh)
        np.testing.assert_allclose(hiw_exp, hiw_out)


if __name__ == "__main__":
    unittest.main()
