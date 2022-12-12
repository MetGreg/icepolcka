"""Tests for the radars module"""
import os
import unittest
import datetime as dt

import tests.utils as test_utils

from icepolcka_utils.database import radars, tables


class RadarDataBaseTest(unittest.TestCase):
    """Tests for the RadarDataBase class"""
    def setUp(self):
        self.file_paths = {'dwd_path': "test_data" + os.sep + "dwd" + os.sep}
        self.db_path = "test_data" + os.sep + "test.db"
        self.radar_db = radars.RadarDataBase(self.file_paths['dwd_path'], self.db_path, False)
        self.time = dt.datetime.now()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_get_data_raises_error(self):
        """Test if the get_data method correctly raises a NotImplementedError"""
        self.assertRaises(NotImplementedError, self.radar_db.get_data, self.time, self.time)

    def test_get_closest_data_raises_error(self):
        """Test if the get_closest_data method correctly raises a NotImplementedError"""
        self.assertRaises(NotImplementedError, self.radar_db.get_closest_data, self.time)

    def test_get_latest_data_raises_error(self):
        """Test if the get_latest_data method correctly raises a NotImplementedError"""
        self.assertRaises(NotImplementedError, self.radar_db.get_latest_data)

    def test_get_update_db_raises_error(self):
        """Test if the update_db method correctly raises a NotImplementedError"""
        self.assertRaises(NotImplementedError, self.radar_db.update_db)


class DWDDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the DWDDataBase class"""
    def setUp(self):
        super().setUp()
        self.file_paths = {'dwd_path': "test_data" + os.sep + "dwd" + os.sep}
        self.db_class = radars.DWDDataBase
        self.radar_db = radars.DWDDataBase(self.file_paths['dwd_path'], self.db_path, False)
        self.time = dt.datetime.now()
        self.start = dt.datetime(2019, 5, 28, 12, 0, 35)  # 1st DWD file
        self.end = dt.datetime(2019, 5, 28, 12, 5, 35)  # 2nd DWD rf file

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.file_paths['dwd_path'], "get_data", self.start,
                       start_time=self.start, end_time=self.end)

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.file_paths['dwd_path'], "get_closest_data", self.start,
                       time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.file_paths['dwd_path'], "get_latest_data", self.end)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.file_paths['dwd_path'], 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.file_paths['dwd_path'], 2)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_update_db_updates_the_database(self):
        """Test if the update_db method correctly updates the db"""
        session = tables.create_session(self.db_path)
        with radars.DWDDataBase(self.file_paths['dwd_path'], self.db_path, update=False) as dwd_db:
            dwd_db.update_db()
        query = session.query(tables.DWDData).all()
        self.assertEqual(len(query), 2)  # There are two DWD files in the data path

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data['time']), "%Y-%m-%d %H:%M:%S")
        return data_time


if __name__ == "__main__":
    unittest.main()
