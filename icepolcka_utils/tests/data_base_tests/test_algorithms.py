"""Tests for the algorithms module"""
import os
import unittest
import datetime as dt

import tests.utils as test_utils

from icepolcka_utils.database import algorithms


class HMCDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the HMCDataBase class"""
    def setUp(self):
        super().setUp()
        self.db_class = algorithms.HMCDataBase
        self.hmc_path = "test_data" + os.sep + "hmc" + os.sep
        self.start = dt.datetime(2019, 5, 28, 12)  # MODEL HMC file
        self.end = dt.datetime(2019, 5, 28, 12, 5)  # DWD HMC file
        self.mp_id = 8  # MODEL MP_ID

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.hmc_path, "get_data", self.start, start_time=self.start,
                       end_time=self.end, source="MODEL", mp_id=self.mp_id, method="Dolan")

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.hmc_path, "get_closest_data", self.start, time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.hmc_path, "get_latest_data", self.end)

    def test_if_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.hmc_path, 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.hmc_path, 2)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data.time), "%Y-%m-%d %H:%M:%S")
        return data_time


if __name__ == "__main__":
    unittest.main()
