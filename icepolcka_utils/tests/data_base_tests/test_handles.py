"""Tests for the handles module"""
import os
import unittest

import xarray as xr

from icepolcka_utils.database import handles


class HandlesTest(unittest.TestCase):
    """Tests for all functions in the handles module"""

    def setUp(self):
        self.wrf_file = "test_data" + os.sep + "wrf" + os.sep + "clouds_d03_2019-05-28_120000"
        self.crsim_file = "test_data" + os.sep + "crsim" + os.sep + "120000.nc"
        self.tracks_file = "test_data" + os.sep + "tracks" + os.sep + "2019-05-28.pkl"

    def test_load_wrf_data_loads_the_data(self):
        """Test if the data is loaded to xarray"""
        dataset = handles.load_wrf_data(self.wrf_file)
        self.assertTrue(isinstance(dataset, xr.Dataset), "Expected xarray Dataset")

    def test_load_xarray_loads_the_data(self):
        """Test if the data is loaded to xarray"""
        dataset = handles.load_xarray(self.crsim_file)
        self.assertTrue(isinstance(dataset, xr.Dataset), "Expected xarray Dataset")


class DWDDataHandlerTest(unittest.TestCase):
    """Tests for the DWDDataHandler class"""
    def setUp(self):
        self.handler = handles.DWDDataHandler()
        self.dwd_file = "test_data" + os.sep + "dwd" + os.sep + "20190528_1200.hd5"

    def test_load_dwd_data_loads_data(self):
        """Test if data is loaded to dict"""
        dataset = self.handler.load_data(self.dwd_file)
        self.assertTrue(isinstance(dataset, dict), "Expected dictionary")


class ResultHandleTest(unittest.TestCase):
    """Tests for the ResultHandle class"""
    def setUp(self):
        self.crsim_file = "test_data" + os.sep + "crsim" + os.sep + "120000.nc"

    def test_load_returns_xarray(self):
        """Test if xarray is returned"""
        attrs = {}

        def load_func():
            return handles.load_xarray(self.crsim_file)

        handle = handles.ResultHandle(attrs, load_func)
        data = handle.load()
        self.assertTrue(isinstance(data, xr.Dataset), "Expected xarray Dataset")


if __name__ == "__main__":
    unittest.main()
