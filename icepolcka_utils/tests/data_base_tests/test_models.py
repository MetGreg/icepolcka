"""Tests for the models module"""
import os
import shutil
import unittest
import datetime as dt

import tests.utils as test_utils

from icepolcka_utils import utils
from icepolcka_utils.database import models, tables


class ModelsTest(unittest.TestCase):
    """Tests for all functions in the models module"""
    def setUp(self):
        self.data_path = "test_data" + os.sep
        self.db_path = utils.make_folder("db")
        self.db_file = self.db_path + "test.db"
        self.start = dt.datetime(2019, 5, 28, 12)  # wrf file
        self.end = dt.datetime(2019, 5, 28, 13)  # wrf file

    def tearDown(self):
        test_utils.delete_content(self.db_path)

    def test_get_wrf_handles_returns_data(self):
        """Test if the get_wrf_handles function returns a data handle"""
        test_cfg = test_utils.create_config(
            self.data_path, self.db_path,
            start=dt.datetime.strftime(self.start, "%d.%m.%Y %H:%M:%S"),
            end=dt.datetime.strftime(self.end, "%d.%m.%Y %H:%M:%S")
            )
        test_cfg['mp'] = 30
        handles, _, _ = models.get_wrf_handles(test_cfg, wrfmp=True, wrfout=True)
        self.assertEqual(len(handles), 1)  # One wrf clouds test files available


class WRFDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the WRFDataBase class"""
    def setUp(self):
        super().setUp()
        self.wrf_path = "test_data" + os.sep + "wrf" + os.sep
        self.tmp_folder = "test_data" + os.sep + "tmp" + os.sep
        self.data_tmp = self.tmp_folder + "clouds_d03_2019-05-28_120000"
        self.db_class = models.WRFDataBase
        self.start = dt.datetime(2019, 5, 28, 12)  # wrf file
        self.end = dt.datetime(2019, 5, 28, 14)  # Latest wrf file
        self.mp_id = 30  # MODEL MP_ID

    def tearDown(self):
        super().tearDown()
        if os.path.exists(self.data_tmp):
            os.remove(self.data_tmp)

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.wrf_path, "get_data", self.start, start_time=self.start,
                       end_time=self.end, mp_id=self.mp_id)

    def test_if_get_closest_data_returns_correct_time(self):
        """Test if the get_closest_method returns the correct time with lower time being closest"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.wrf_path, "get_closest_data", self.start, time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.wrf_path, "get_latest_data", self.end)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.wrf_path, 4)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.wrf_path, 4)

    def test_if_error_is_raised_for_multiple_datasets(self):
        """Test if error is raised when multiple datasets are found for the same time"""
        session = tables.create_tables(self.db_path)
        with models.WRFDataBase(self.wrf_path, self.db_path, update=False) as wrf_db:
            wrf_db.update_db()

        # Create a scenario where multiple datasets have the same time stamp
        model = session.query(tables.Model).filter_by(name="WRF").one()
        data = session.query(tables.ModelData).filter_by(model=model).first()
        dataset1 = data.dataset
        filename = dataset1.clouds_file.filename
        dataset2 = session.query(tables.Dataset).all()[-1]
        dataset2.start_time = dataset1.start_time
        dataset2.end_time = dataset1.end_time
        session.commit()
        session.close()

        shutil.copyfile(filename, self.data_tmp)

        with models.WRFDataBase(self.tmp_folder, self.db_path, update=False) as wrf_db:
            self.assertRaises(AssertionError, wrf_db.update_db)

    def _run_test(self, data, exp_time):
        data_time = self._get_time(data)
        self.assertEqual(data_time, exp_time)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data['Time'].values[0]), "%Y-%m-%dT%H:%M:%S.%f000")
        return data_time

    @staticmethod
    def _load_data(handle):
        try:
            handle = handle[0]
        except KeyError:
            pass
        try:
            handle = handle['clouds']
        except KeyError:
            handle = handle['wrfout']
        data = handle.load()
        return data


class CRSIMDataBaseTest(test_utils.GeneralDataBaseTest):
    """Tests for the CRSIMDataBase class"""
    def setUp(self):
        super().setUp()
        self.crsim_path = "test_data" + os.sep + "crsim" + os.sep
        self.db_class = models.CRSIMDataBase
        self.start = dt.datetime(2019, 5, 28, 12)  # crsim file
        self.end = dt.datetime(2019, 5, 28, 12, 5)  # 2nd crsim file
        self.mp_id = 8  # MODEL MP_ID

    def test_if_get_data_returns_correct_time(self):
        """Test the get_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.crsim_path, "get_data", self.start,
                       start_time=self.start, end_time=self.end, mp_id=self.mp_id, hm="all",
                       radar="Isen")

    def test_if_get_closest_data_returns_correct_time(self):
        """Test the get_closest_data method by calling testing method of super class"""
        test_time = self.start + dt.timedelta(seconds=60)
        self.time_test(self.db_class, self.crsim_path, "get_closest_data", self.start,
                       time=test_time)

    def test_if_get_latest_data_returns_correct_time(self):
        """Tests the get_latest_data method by calling testing method of super class"""
        self.time_test(self.db_class, self.crsim_path, "get_latest_data", self.end)

    def test_wrong_file_types_are_ignored(self):
        """Test if file types that are wrong are ignored"""
        self.assert_datafiles(self.db_class, self.wrong_path, 0)

    def test_if_preloaded_files_are_ignored(self):
        """Test if the files that have been added to db already are ignored"""
        self.assert_datafiles(self.db_class, self.crsim_path, 2)
        # Repeat to update db again and see if number of entries does not change
        self.assert_datafiles(self.db_class, self.crsim_path, 2)

    @staticmethod
    def _get_time(data):
        data_time = dt.datetime.strptime(str(data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")
        return data_time


if __name__ == "__main__":
    unittest.main()
