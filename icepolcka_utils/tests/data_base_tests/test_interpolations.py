"""Tests for the interpolations module"""
import os
import unittest
import datetime as dt

import tests.utils as test_utils

from icepolcka_utils.database import interpolations


class RFDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the RFDataBase class"""
    def setUp(self):
        super().setUp()
        self.rf_path = "test_data" + os.sep + "rf" + os.sep
        self.db_class = interpolations.RFDataBase
        self.start = dt.datetime(2019, 5, 28, 12)  # MODEL rf file
        self.end = dt.datetime(2019, 5, 28, 12, 5)  # 2nd MODEL rf file
        self.mp_id = 8  # MODEL MP_ID
        self.radar = "Isen"  # Radar of test data

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.rf_path, "get_data", self.start, start_time=self.start,
                       end_time=self.end, mp_id=self.mp_id, radar=self.radar)

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.rf_path, "get_closest_data", self.start, time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.rf_path, "get_latest_data", self.end)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.rf_path, 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.rf_path, 2)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")
        return data_time


class RGDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the RGDataBase class"""
    def setUp(self):
        super().setUp()
        self.rg_path = "test_data" + os.sep + "rg" + os.sep
        self.db_class = interpolations.RGDataBase
        self.start = dt.datetime(2019, 5, 28, 12)  # MODEL rg file
        self.end = dt.datetime(2019, 5, 28, 12, 5, 35)  # DWD rg file
        self.mp_id = 8  # MODEL MP_ID
        self.radar = "Isen"  # Radar of test data

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.rg_path, "get_data", self.start, start_time=self.start,
                       end_time=self.end, mp_id=self.mp_id, radar=self.radar)

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.rg_path, "get_closest_data", self.start, time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.rg_path, "get_latest_data", self.end)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.rg_path, 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.rg_path, 2)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data.time), "%Y-%m-%d %H:%M:%S")
        return data_time


class TempDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the TempDataBase class"""
    def setUp(self):
        super().setUp()
        self.temp_path = "test_data" + os.sep + "temp" + os.sep
        self.db_class = interpolations.TempDataBase
        self.start = dt.datetime(2019, 5, 28, 12)  # MODEL temp file
        self.end = dt.datetime(2019, 5, 28, 12, 5)  # 2nd MODEL temp file
        self.mp_id = 8  # MODEL MP_ID

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.temp_path, "get_data", self.start, start_time=self.start,
                       end_time=self.end, mp_id=self.mp_id)

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.temp_path, "get_closest_data", self.start,
                       time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.temp_path, "get_latest_data", self.end)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.temp_path, 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.temp_path, 2)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")
        return data_time


if __name__ == "__main__":
    unittest.main()
