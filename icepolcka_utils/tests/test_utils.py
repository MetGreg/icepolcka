"""Tests for utils module"""
import os
import unittest
import datetime as dt

import numpy as np

import tests.utils as test_utils

from icepolcka_utils import utils


class UtilsTest(unittest.TestCase):
    """Tests for all functions in the utils module"""

    def setUp(self):
        self.tmp = utils.make_folder("tmp")
        self.db_path = utils.make_folder("db")

    def tearDown(self):
        test_utils.delete_content(self.tmp)
        test_utils.delete_content(self.db_path)

    def test_make_folder_makes_folder(self):
        """Test if the output folder is created"""
        folder = utils.make_folder(self.tmp, mp_id=8, radar="Poldirad", date=dt.datetime.now(),
                                   hm_name="rain")
        self.assertTrue(os.path.exists(folder))

    def test_make_folder_passes_if_folder_exists(self):
        """Test if function works when folder already exists"""
        utils.make_folder(self.tmp, mp_id=8, radar="Poldirad", date=dt.datetime.now(),
                          hm_name="rain")
        # Repeat to see what happens when folder was created already before
        folder = utils.make_folder(self.tmp, mp_id=8, radar="Poldirad", date=dt.datetime.now(),
                                   hm_name="rain")
        self.assertTrue(os.path.exists(folder))

    def test_make_folder_makes_correct_number_of_subfolders(self):
        """Test if the number of subfolders created is correct"""
        utils.make_folder(self.tmp, mp_id=8, radar="Poldirad", date=dt.datetime.now(),
                          hm_name="rain")

        # Test if number of subfolders are as expected
        subfolders = self._fcount(self.tmp)
        self.assertEqual(subfolders, 6)  # mp, radar, hm, year, month, day

    def test_make_folder_returns_correct_path_if_folder_exists_already(self):
        """Test if function works correctly when folder already exists"""
        # Test existing folder
        folder = utils.make_folder(self.tmp, mp_id=8, radar="Poldirad", date=dt.datetime.now(),
                                   hm_name="rain")
        self.assertTrue(os.path.exists(folder))

    def test_get_mean_angle_returns_correct_angle(self):
        """Test if the mean angle calculated is correct"""
        mean = utils.get_mean_angle(177, 187)
        self.assertEqual(mean, 182, "Expected mean to be at 182 degrees.")

    def test_get_mean_angle_returns_correct_angle_for_angles_above_and_below_360(self):
        """Test if the angle is correct when the two input angles are below and above 360"""
        mean = utils.get_mean_angle(355, 6)
        self.assertEqual(mean, 0.5, "Expected mean to be at 0.5 degrees.")

    def test_get_mean_angle_raises_error_when_azimuth_are_wrong(self):
        """Test if ValueError is raised when azimuth not between 0 and 360"""
        self.assertRaises(ValueError, utils.get_mean_angle, 361, 5)

    def test_get_cfg_loads_model_source_correctly(self):
        """Test if the get_cfg function returns the correct source when source is MODEL"""
        cfg_in = test_utils.create_config(self.tmp, self.db_path, time="str")
        cfg_file = self.tmp + "test.yaml"
        test_utils.write_config(cfg_in, cfg_file)
        cfg_out = utils.get_cfg(cfg_file)
        self.assertEqual(cfg_in['source'], cfg_out['source'], "Expected output source to equal "
                                                              "input source")

    def test_get_cfg_loads_puts_mp_to_none_when_source_is_dwd(self):
        """Test if the get_cfg function puts the mp_id to none if the source is DWD"""
        cfg_in = test_utils.create_config(self.tmp, self.db_path, time="str")
        cfg_in['source'] = "DWD"
        cfg_file = self.tmp + "test.yaml"
        test_utils.write_config(cfg_in, cfg_file)
        cfg_out = utils.get_cfg(cfg_file)
        self.assertTrue(cfg_out['mp'] is None)

    def test_get_cfg_works_correctly_when_source_does_not_exist(self):
        """Test if the get_cfg function works if the source does not exist"""
        cfg_in = test_utils.create_config(self.tmp, self.db_path, time="str")
        del cfg_in['source']
        cfg_file = self.tmp + "test.yaml"
        test_utils.write_config(cfg_in, cfg_file)
        cfg_out = utils.get_cfg(cfg_file)
        self.assertEqual(cfg_out['mp'], cfg_in['mp'], "Expected output mp to equal input mp")

    @staticmethod
    def test_mask_data_returns_correct_masked_array():
        """Test if the mask_data function returns the array as expected"""
        idx = np.index_exp[16, 180, 180]
        shape = (152, 360, 360)
        data = np.random.randint(0, 10, shape)
        data = data.astype("float64")
        mask = np.full(shape, False)
        mask[idx] = True
        masked = utils.mask_data(data, mask)
        exp_array = data.copy()
        exp_array[idx] = np.nan
        np.testing.assert_allclose(exp_array, masked)

    @staticmethod
    def _fcount(path):
        count1 = 0
        for _, dirs, _ in os.walk(path):
            count1 += len(dirs)
        return count1


class ConfigTest(unittest.TestCase):
    """Tests for the Config class"""
    def setUp(self):
        self.tmp = utils.make_folder("tmp")
        self.config_file = self.tmp + "config.yaml"
        self.config = utils.Config()

    def tearDown(self):
        test_utils.delete_content(self.tmp)

    def test_if_config_is_loaded_correctly(self):
        """Test if the load_config method loads the information correctly"""
        cfg_in = test_utils.create_config(self.tmp, time="str")
        test_utils.write_config(cfg_in, self.config_file)
        self.config.load_config(self.config_file)
        exp_date = dt.datetime.strptime(cfg_in['date'], "%d.%m.%Y")
        self.assertEqual(self.config.cfg['date'], exp_date, "Expected different date")

    def test_if_load_config_works_without_start_time(self):
        """Test if the load_config method loads the information correctly when no start is given"""
        cfg_in = test_utils.create_config(self.tmp, time="str")
        del cfg_in['start']
        test_utils.write_config(cfg_in, self.config_file)
        self.config.load_config(self.config_file)
        exp_date = dt.datetime.strptime(cfg_in['date'], "%d.%m.%Y")
        self.assertEqual(self.config.cfg['date'], exp_date, "Expected different date")

    def test_if_load_config_works_without_end_time(self):
        """Test if the load_config method loads the information correctly when no end is given"""
        cfg_in = test_utils.create_config(self.tmp, time="str")
        del cfg_in['end']
        test_utils.write_config(cfg_in, self.config_file)
        self.config.load_config(self.config_file)
        exp_date = dt.datetime.strptime(cfg_in['date'], "%d.%m.%Y")
        self.assertEqual(self.config.cfg['date'], exp_date, "Expected different date")

    def test_if_load_config_works_without_date(self):
        """Test if the load_config method loads the information correctly when no date is given"""
        cfg_in = test_utils.create_config(self.tmp, time="str")
        del cfg_in['date']
        test_utils.write_config(cfg_in, self.config_file)
        self.config.load_config(self.config_file)
        exp_date = dt.datetime.strptime(cfg_in['start'], "%d.%m.%Y %H:%M:%S")
        self.assertEqual(self.config.cfg['start'], exp_date, "Expected different start date")


if __name__ == "__main__":
    unittest.main()
