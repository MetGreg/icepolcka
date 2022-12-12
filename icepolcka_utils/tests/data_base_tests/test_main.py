"""Tests for the main module"""
import os
import unittest
import datetime as dt

import tests.utils as test_utils

from icepolcka_utils import utils
from icepolcka_utils.database import interpolations, main, tables


class FunctionTest(unittest.TestCase):
    """Tests for all functions in the main database module"""

    def setUp(self):
        self.data_path = "test_data" + os.sep
        self.db_path = utils.make_folder("db")
        self.db_file = self.db_path + "test.db"
        self.start = dt.datetime(2019, 5, 28, 12)  # MODEL rg file
        self.end = dt.datetime(2019, 5, 28, 12, 5, 35)  # DWD rg file
        self.mp_id = 8  # MODEL rg MP-ID

    def tearDown(self):
        test_utils.delete_content(self.db_path)

    def test_get_closest_time_returns_correct_time_with_lesser_time(self):
        """Test if the get_closest method finds correct time when input time is later than data"""
        # Define testing times
        time1 = dt.datetime(2019, 7, 1, 13)
        time_lesser = dt.datetime(2019, 7, 1, 12, 48)

        # Create a database entry and a query object that will be passed
        session = tables.create_session(self.db_file)
        session = self._add_data_to_db(session, "test.nc", time1)
        query = session.query(tables.CRSIMData)

        # Run function input time before expected time
        closest_lesser = main.get_closest(query, tables.CRSIMData.time, time_lesser)
        self.assertEqual(closest_lesser.time, time1, "Expected time equal to" + str(time1))

        # Close database
        session.close()

    def test_closest_time_returns_correct_time_with_greater_time(self):
        """Test if the get_closest method finds correct time when input time is earlier than data"""
        # Define testing times
        time1 = dt.datetime(2019, 7, 1, 13)
        time_greater = dt.datetime(2019, 7, 1, 13, 5)

        # Create a database entry and a query object that will be passed
        session = tables.create_session(self.db_file)
        session = self._add_data_to_db(session, "test.nc", time1)
        query = session.query(tables.CRSIMData)

        # Run function input time after expected time
        closest_greater = main.get_closest(query, tables.CRSIMData.time, time_greater)
        self.assertEqual(closest_greater.time, time1, "Expected time equal to" + str(time1))

        # Close database
        session.close()

    def test_closest_time_returns_correct_time_in_between_two_times_closer_to_lower_time(self):
        """Test if the get_closest method finds correct time when input time is in between data"""
        # Define testing times
        time1 = dt.datetime(2019, 7, 1, 13)
        time2 = dt.datetime(2019, 7, 1, 14)
        test_time = dt.datetime(2019, 7, 1, 13, 15)

        # Create a database entry and add two entries to database
        session = tables.create_session(self.db_file)
        self._add_data_to_db(session, "test.nc", time1)
        session = self._add_data_to_db(session, "test2.nc", time2)
        query = session.query(tables.CRSIMData)

        # Run method again to see if correct database entry is returned
        closest = main.get_closest(query, tables.CRSIMData.time, test_time)
        self.assertEqual(closest.time, time1, "Expected time equal to" + str(time1))

        # Close database
        session.close()

    def test_closest_time_returns_correct_time_in_between_two_times_closer_to_upper_time(self):
        """Test if the get_closest method finds correct time when input time is in between data"""
        # Define testing times
        time1 = dt.datetime(2019, 7, 1, 13)
        time2 = dt.datetime(2019, 7, 1, 14)
        test_time = dt.datetime(2019, 7, 1, 13, 45)

        # Create a database entry and add two entries to database
        session = tables.create_session(self.db_file)
        self._add_data_to_db(session, "test.nc", time1)
        session = self._add_data_to_db(session, "test2.nc", time2)
        query = session.query(tables.CRSIMData)

        # Run method again to see if correct database entry is returned
        closest = main.get_closest(query, tables.CRSIMData.time, test_time)
        self.assertEqual(closest.time, time2, "Expected time equal to" + str(time2))

        # Close database
        session.close()

    def test_get_handles_returns_data(self):
        """Test if the get_handles function returns a data handle"""
        test_config = test_utils.create_config(
            self.data_path, self.db_path,
            start=dt.datetime.strftime(self.start, "%d.%m.%Y %H:%M:%S"),
            end=dt.datetime.strftime(self.end, "%d.%m.%Y %H:%M:%S")
            )
        handles = main.get_handles(interpolations.RGDataBase, test_config, "RG")
        self.assertEqual(len(handles), 2)  # Two test files available

    def test_get_handles_removes_mp_when_source_is_dwd(self):
        """Test if the mp-id is removed from config if the source is DWD"""
        test_config = test_utils.create_config(
            self.data_path, self.db_path,
            start=dt.datetime.strftime(self.start, "%d.%m.%Y %H:%M:%S"),
            end=dt.datetime.strftime(self.end, "%d.%m.%Y %H:%M:%S")
            )
        test_config['source'] = "DWD"
        handles = main.get_handles(interpolations.RGDataBase, test_config, "RG", source="DWD",
                                   mp_id=self.mp_id)
        self.assertEqual(len(handles), 1)  # One DWD test file available

    def test_update_db_updates_database(self):
        """Test if the update_db function updates the db"""
        test_config = test_utils.create_config(
            self.data_path, self.db_path,
            start=dt.datetime.strftime(self.start, "%d.%m.%Y %H:%M:%S"),
            end=dt.datetime.strftime(self.end, "%d.%m.%Y %H:%M:%S")
            )
        main.update_db(interpolations.RGDataBase, test_config, "RG")
        session = tables.create_session(self.db_path + os.sep + "rg.db")
        query = session.query(tables.RGData).all()
        self.assertEqual(len(query), 2)  # Two test files available
        session.close()

    def _add_data_to_db(self, session, filename, time):
        radar = tables.Radar(name="Isen")
        hm_name = tables.Hydrometeor(name="all")
        crsim_data = tables.CRSIMData(file_path=filename, time=time, mp_id=self.mp_id, radar=radar,
                                      hm=hm_name)
        session.add(crsim_data)
        session.commit()
        return session


class DataBaseTest(unittest.TestCase):
    """Tests for the DataBase class"""
    def setUp(self):
        self.db_path = "test_data" + os.sep + "test.db"
        self.data_base = main.DataBase("test_data", self.db_path, False)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_get_data_raises_error(self):
        """Test if the get_data method raises NotImplementedError"""
        self.assertRaises(NotImplementedError, self.data_base.get_data, dt.datetime.now(),
                          dt.datetime.now())

    def test_closest_get_data_raises_error(self):
        """Test if the get_closest_data method raises NotImplementedError"""
        self.assertRaises(NotImplementedError, self.data_base.get_closest_data, dt.datetime.now())

    def test_latest_get_data_raises_error(self):
        """Test if the get_latest_data method raises NotImplementedError"""
        self.assertRaises(NotImplementedError, self.data_base.get_latest_data)

    def test_update_db_raises_error(self):
        """Test if the update_db method correctly raises a NotImplementedError"""
        self.assertRaises(NotImplementedError, self.data_base.update_db)


if __name__ == "__main__":
    unittest.main()
