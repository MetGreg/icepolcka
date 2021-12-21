"""Tests for grid module"""
import os
import pytz
import unittest
import datetime as dt
import numpy as np
from icepolcka_utils.grid import create_column, get_pyart_grids, \
    get_pyart_grid, PyArtGrid

from icepolcka_utils.data_base import RGDataBase


class GridTest(unittest.TestCase):

    def setUp(self):
        self.db_path = "data" + os.sep + "rg.db"
        self.grid_path = "data" + os.sep + "rg" + os.sep
        with RGDataBase(self.grid_path, self.db_path) as grid_db:
            self.handle = grid_db.get_latest_data(mp_id=8)[0]

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @staticmethod
    def test_create_column():
        coords = np.array([10, 50])
        heights = np.array([1000, 2000])
        grid = create_column(coords, heights)
        exp_grid = np.array([[10, 50, 1000], [10, 50, 2000]])
        np.testing.assert_array_equal(grid, exp_grid)

    def test_get_pyart_grids(self):
        handles = [self.handle, self.handle]
        grids = get_pyart_grids(handles, var="Zhh")
        exp_grid = get_pyart_grid(self.handle.load(), var="Zhh")
        time_out = dt.datetime.utcfromtimestamp(grids[0].time['data'][0])
        exp_time = dt.datetime.utcfromtimestamp(exp_grid.time['data'][0])
        self.assertEqual(time_out, exp_time)

    def test_get_pyart_grid(self):
        grid_ds = self.handle.load()
        grid = get_pyart_grid(grid_ds, var="Zhh")
        time_out = dt.datetime.utcfromtimestamp(grid.time['data'][0])
        exp_time = dt.datetime(2019, 7, 1, 13, 0, 0)
        self.assertEqual(time_out, exp_time)


class PyArtGridTest(unittest.TestCase):

    def setUp(self):
        self.data, self.data_masked = self.make_data()
        time = dt.datetime.utcnow()
        self.time = time.replace(tzinfo=pytz.utc).replace(microsecond=0)
        self.grid = self.make_2D_grid()
        self.params = {'FIELD_THRESH': 32, 'MIN_SIZE': 3, 'GS_ALT': 1500}

    def tearDown(self):
        pass

    def test_extract_grid_data(self):
        field = "reflectivity"
        grid_size = np.array([np.nan, 1000, 1000])
        raw, frame = self.grid.extract_grid_data(field, grid_size, self.params)
        exp_frame = np.array([[0, 0, 0], [0, 0, 0], [1, 1, 1]])
        np.testing.assert_array_equal(raw, self.data)
        np.testing.assert_array_equal(frame, exp_frame)

    def test_parse_grid_datetime(self):
        time = self.grid.parse_grid_datetime()
        self.assertEqual(time, self.time)

    def test_get_grid_alt(self):
        # Test 2D grid
        alt = self.grid.get_grid_alt(2000)
        self.assertEqual(alt, 0)

        # Test 3D grid
        self.grid.z['data'] = np.array([0, 1000])
        self.grid.grid_size[0] = 1000
        alt = self.grid.get_grid_alt(400)
        max_alt = self.grid.get_grid_alt(1500)
        self.assertEqual(alt, 0)
        self.assertEqual(max_alt, 1)

    def make_2D_grid(self):
        time = int(dt.datetime.timestamp(self.time))
        x = {'data': np.arange(0, 2001, 1000)}
        y = {'data': np.arange(0, 2001, 1000)}
        z = {'data': np.array([0])}
        lon = np.array([[10, 10.5, 11], [10, 10.5, 11], [10, 10.5, 11]])
        lat = np.array([[48, 48, 48], [49, 49, 49], [50, 50, 50]])
        time = {'data': [np.array(time)], 'units': 'seconds since 1970-01-01'}
        fields = {'reflectivity': {'data': self.data_masked}}
        grid = PyArtGrid(time, fields, x, y, z, lon, lat)
        return grid

    @staticmethod
    def make_data():
        data = np.array([[11, 12, 13], [23, 24, 25], [36, 37, 38]])
        data_masked = np.ma.masked_array([data])
        return data, data_masked


if __name__ == "__main__":
    unittest.main()
