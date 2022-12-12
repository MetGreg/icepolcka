"""Tests for grid module"""
import os
import unittest
import datetime as dt

import pytz
import numpy as np

from tests import utils as test_utils

from icepolcka_utils import grid
from icepolcka_utils.database import handles


class GridTest(unittest.TestCase):
    """Tests for all functions in the grid module"""

    def setUp(self):
        self.rg_file = "test_data" + os.sep + "rg" + os.sep + "120000.nc"
        self.time = dt.datetime(2019, 5, 28, 12)  # Time of rg file

    def test_get_pyart_grid_returns_correct_date(self):
        """Test if the grid returned as correct date"""
        grid_ds = handles.load_xarray(self.rg_file)
        grid_out = grid.get_pyart_grid(grid_ds)
        time_out = dt.datetime.utcfromtimestamp(grid_out.time['data'][0])
        self.assertEqual(time_out, self.time)

    @staticmethod
    def test_create_column_creates_a_column_as_expected():
        """Test if the column for given scenario is calculated as expected"""
        coords = np.array([10, 50])
        heights = np.array([1000, 2000])
        col = grid.create_column(coords, heights)
        exp_col = np.array([[10, 50, 1000], [10, 50, 2000]])  # Calculated by hand
        np.testing.assert_array_equal(col, exp_col)


class PyArtGridTest(unittest.TestCase):
    """Tests for the PyArtGrid class"""

    def setUp(self):
        self.data, self.data_masked = self._make_data()
        time = dt.datetime.utcnow()
        self.time = time.replace(tzinfo=pytz.utc).replace(microsecond=0)
        self.grid = test_utils.make_pyart_grid(self.data_masked, self.time)
        self.params = {'FIELD_THRESH': 32, 'MIN_SIZE': 3, 'GS_ALT': 1500}

    def test_extract_grid_data_returns_correct_raw_grid(self):
        """Test if the raw_grid that is returned is as expected"""
        field = "reflectivity"
        grid_size = np.array([np.nan, 1000, 1000])
        raw, _ = self.grid.extract_grid_data(field, grid_size, self.params)
        np.testing.assert_array_equal(raw, self.data)  # Raw frame should equal input data

    def test_extract_grid_data_returns_correct_frame(self):
        """Test if the filtered frame that is returned is as expected"""
        field = "reflectivity"
        grid_size = np.array([np.nan, 1000, 1000])
        _, frame = self.grid.extract_grid_data(field, grid_size, self.params)
        exp_frame = np.array([[0, 0, 0], [0, 0, 0], [1, 1, 1]])
        np.testing.assert_array_equal(frame, exp_frame)

    def test_parse_grid_datetime_returns_correct_time(self):
        """Test if the parse_grid_datetime method returns the expected time"""
        time = self.grid.parse_grid_datetime()
        self.assertEqual(time, self.time)  # Time must equal input time

    def test_get_grid_alt_returns_correct_height_2d(self):
        """Test if the correct height is returned in case of a 2D grid"""
        alt = self.grid.get_grid_alt(2000)
        self.assertEqual(alt, 0)

    def test_get_grid_alt_returns_correct_height_3d_at_lower_boundary(self):
        """Test if the correct height is returned in case of a 3D grid at lower boundary"""
        self.grid.z['data'] = np.array([0, 1000])
        self.grid.grid_size[0] = 1000
        alt = self.grid.get_grid_alt(400)  # 400 closer to 0, than to 1000
        self.assertEqual(alt, 0)

    def test_get_grid_alt_returns_correct_height_3d_at_upper_boundary(self):
        """Test if the correct height is returned in case of a 3D grid at upper boundary"""
        self.grid.z['data'] = np.array([0, 1000])
        self.grid.grid_size[0] = 1000
        alt = self.grid.get_grid_alt(1500)  # 1500 above upper boundary --> closer to 1000 than 0
        self.assertEqual(alt, 1)

    @staticmethod
    def _make_data():
        data = np.array([[11, 12, 13], [23, 24, 25], [36, 37, 38]])
        data_masked = np.ma.masked_array([data])
        return data, data_masked


if __name__ == "__main__":
    unittest.main()
