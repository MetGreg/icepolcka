"""Tests for tracks module"""
import pytz
import unittest
import datetime as dt
import numpy as np
import pandas as pd

from icepolcka_utils.tracks import CellTracks, TrackRecord
from icepolcka_utils.grid import PyArtGrid

PARAMS = {
    'FIELD_THRESH': 32,
    'MIN_SIZE': 3,
    'SEARCH_MARGIN': 4000,
    'FLOW_MARGIN': 10000,
    'MAX_FLOW_MAG': 50,
    'MAX_DISPARITY': 999,
    'MAX_SHIFT_DISP': 15,
    'ISO_THRESH': 8,
    'ISO_SMOOTH': 3,
    'GS_ALT': 1500
    }


def make_grids(data1, data2, data3, time1, time2, time3):
    time1 = int(dt.datetime.timestamp(time1))
    time2 = int(dt.datetime.timestamp(time2))
    time3 = int(dt.datetime.timestamp(time3))
    x = {'data': np.arange(0, 2001, 1000)}
    y = {'data': np.arange(0, 2001, 1000)}
    z = {'data': np.array([0])}
    lon = np.array([[10, 10.5, 11], [10, 10.5, 11], [10, 10.5, 11]])
    lat = np.array([[48, 48, 48], [49, 49, 49], [50, 50, 50]])
    time1 = {'data': [np.array(time1)], 'units': 'seconds since 1970-01-01'}
    time2 = {'data': [np.array(time2)], 'units': 'seconds since 1970-01-01'}
    time3 = {'data': [np.array(time3)], 'units': 'seconds since 1970-01-01'}
    field1 = {'reflectivity': {'data': data1}}
    field2 = {'reflectivity': {'data': data2}}
    field3 = {'reflectivity': {'data': data3}}
    grid1 = PyArtGrid(time1, field1, x, y, z, lon, lat)
    grid2 = PyArtGrid(time2, field2, x, y, z, lon, lat)
    grid3 = PyArtGrid(time3, field3, x, y, z, lon, lat)
    return grid1, grid2, grid3


class CellTracksTest(unittest.TestCase):

    def setUp(self):
        data = np.ma.masked_array(
            [np.array([[11, 12, 13], [23, 24, 25], [36, 38, 37]])]
            )
        empty = np.ma.masked_array(
            [np.array([[11, 12, 13], [14, 15, 16], [17, 18, 19]])]
            )
        time1 = dt.datetime(2019, 7, 1, 13, 0)
        time2 = dt.datetime(2019, 7, 1, 13, 5)
        time3 = dt.datetime(2019, 7, 1, 13, 10)
        self.time1 = time1.replace(tzinfo=pytz.utc)
        self.time2 = time2.replace(tzinfo=pytz.utc)
        self.time3 = time3.replace(tzinfo=pytz.utc)
        self.grid1, self.grid2, self.grid3 = make_grids(data, data, data,
                                                        self.time1,
                                                        self.time2, self.time3)
        self.empty1, self.empty2, self.empty3 = make_grids(
            empty, empty, empty, self.time1, self.time2, self.time3
            )
        self.cell_tracks = CellTracks(PARAMS)
        self.cell_tracks2 = CellTracks(PARAMS)

    def tearDown(self):
        pass

    def test_get_tracks(self):
        self.cell_tracks.get_tracks(iter([self.grid1, self.grid2, self.grid3]))
        self.assertEqual(len(self.cell_tracks.tracks), 3)
        self.assertEqual(self.cell_tracks.tracks.iloc[0, 0], self.time1)
        self.assertEqual(self.cell_tracks.tracks.iloc[1, 0], self.time2)
        self.assertEqual(self.cell_tracks.tracks.iloc[2, 0], self.time3)

        # Test data without valid cells
        self.cell_tracks2.get_tracks(iter([self.empty1, self.empty2]))
        self.assertEqual(len(self.cell_tracks2.tracks), 0)

    def test_get_object_prop(self):
        self.cell_tracks.get_tracks(iter([self.grid1, self.grid2]))
        grid_size = np.array([np.nan, 1000, 1000])
        raw, image = self.grid1.extract_grid_data("reflectivity", grid_size,
                                                  PARAMS)
        prop = self.cell_tracks.get_object_prop(image, self.grid1)
        self.assertEqual(prop['id1'], [1])
        np.testing.assert_array_equal(prop['center'][0], np.array([2, 1]))
        self.assertEqual(prop['grid_x'], [1])
        self.assertEqual(prop['grid_y'], [2])
        self.assertEqual(prop['area'], [3])
        self.assertTrue(np.isnan(prop['volume'][0]))
        self.assertEqual(prop['field_max'], [38])
        self.assertEqual(prop['lon'], [10.5])
        self.assertEqual(prop['lat'], [50])
        self.assertTrue(prop['isolated'][0])

    def test_write_tracks(self):
        old_tracks = pd.DataFrame()
        record = TrackRecord(self.grid1)
        record.scan = 1
        objects = {'uid': 1}
        obj_props = {'id1': [1], 'grid_x': 1, 'grid_y': 1, 'lon': 53,
                     'lat': 13, 'area': 100, 'volume': 1000, 'field_max': 50,
                     'max_height': 12, 'isolated': True, 'mask': [True]}
        tracks = self.cell_tracks.write_tracks(old_tracks, record, objects,
                                               obj_props)
        self.assertEqual(tracks.loc[[1]]['lon'].values[0], 53)


class TrackRecordTest(unittest.TestCase):

    def setUp(self):
        data = np.ma.masked_array(
            [np.array([[11, 12, 13], [23, 24, 25], [36, 38, 37]])]
            )
        time = dt.datetime(2019, 7, 1, 13, 0)
        self.time = time.replace(tzinfo=pytz.utc)
        self.grid1, self.grid2, self.grid3 = make_grids(
            data, data, data, self.time, self.time, self.time
            )
        self.record = TrackRecord(self.grid1)

    def tearDown(self):
        pass

    def test_update_scan_and_time(self):
        self.record.update_scan_and_time(self.grid1)
        self.assertEqual(self.record.time, self.time)


if __name__ == "__main__":
    unittest.main()
