"""Tests for plots module"""
import cartopy
import matplotlib
import os
import pytz
import unittest
import datetime as dt
import numpy as np
import cartopy.crs as ccrs
import matplotlib.pyplot as plt

from icepolcka_utils.grid import PyArtGrid
from icepolcka_utils.plots import create_figure, add_cities, add_features, \
    plot_background, add_grid, plot_tracks, Tracer
from icepolcka_utils.tracks import CellTracks


EXTENT = [10.53, 12.65, 47.43, 48.85]
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
    'GS_ALT': 1500,
    }


def create_grids(dim="2D"):
    data1 = np.ma.masked_array(
        np.array([[11, 12, 13], [23, 24, 25], [36, 38, 37]])
        )
    data2 = np.ma.masked_array(
        np.array([[11, 12, 13], [14, 15, 16], [17, 18, 19]])
        )
    time1 = dt.datetime(year=2019, month=7, day=1, hour=13,
                        minute=0).replace(tzinfo=pytz.utc)
    time2 = dt.datetime(year=2019, month=7, day=1, hour=13,
                        minute=5).replace(tzinfo=pytz.utc)
    time1 = int(dt.datetime.timestamp(time1))
    time2 = int(dt.datetime.timestamp(time2))
    x = {'data': np.arange(0, 2001, 1000)}
    y = {'data': np.arange(0, 2001, 1000)}
    if dim == '2D':
        z = {'data': np.array([0])}
        data1 = np.ma.masked_array([data1])
        data2 = np.ma.masked_array([data2])
    elif dim == '3D':
        z = {'data': np.array([0, 1000])}
        data1 = np.tile(data1, (2, 1, 1))
        data2 = np.tile(data2, (2, 1, 1))
    lon = np.array([[10, 10.5, 11], [10, 10.5, 11], [10, 10.5, 11]])
    lat = np.array([[48, 48, 48], [49, 49, 49], [50, 50, 50]])
    time1 = {'data': np.array([time1]), 'units': "seconds since 1970-01-01"}
    time2 = {'data': np.array([time2]), 'units': "seconds since 1970-01-01"}
    field1 = {'reflectivity': {'data': data1}}
    field2 = {'reflectivity': {'data': data2}}
    grid1 = PyArtGrid(time1, field1, x, y, z, lon, lat)
    grid2 = PyArtGrid(time2, field2, x, y, z, lon, lat)
    return [grid1, grid2]


class PlotsTest(unittest.TestCase):

    def setUp(self):
        self.fig, self.ax = create_figure()
        self.output_dir = "output" + os.sep

    def tearDown(self):

        for subdir, dirs, files in os.walk(self.output_dir):
            for file in sorted(files):
                if file.endswith(".png"):
                    os.remove(subdir + os.sep + file)

    def test_create_figure(self):
        fig, ax = create_figure()
        self.assertEqual(type(fig), matplotlib.figure.Figure)
        self.assertEqual(type(ax), cartopy.mpl.geoaxes.GeoAxesSubplot)

    def test_add_cities(self):
        cities = ["München", "Augsburg"]
        ax = add_cities(self.ax, cities)
        self.assertEqual(type(ax), cartopy.mpl.geoaxes.GeoAxesSubplot)

    def test_add_features(self):
        ax = add_features(self.ax)
        self.assertEqual(type(ax), cartopy.mpl.geoaxes.GeoAxesSubplot)

    def test_plot_background(self):
        ax = plot_background(self.ax, EXTENT)
        self.assertEqual(type(ax), cartopy.mpl.geoaxes.GeoAxesSubplot)

    def test_add_grid(self):
        ax = add_grid(self.ax)
        self.assertEqual(type(ax), cartopy.mpl.geoaxes.GeoAxesSubplot)

    def test_plot_tracks(self):
        cities = []
        levels = np.arange(0, 55, 2)
        grids = create_grids("2D")
        tobj = CellTracks(PARAMS)
        tobj.get_tracks(iter(grids))
        plot_tracks(tobj, grids, EXTENT, levels, cities, self.output_dir,
                    cell_text=True)
        plots = os.listdir(self.output_dir)
        self.assertTrue(len(plots) > 0)


class TracerTest(unittest.TestCase):

    def setUp(self):
        self.data_path = "data"
        grids = create_grids("2D")
        grids = grids*2
        self.tobj = CellTracks(PARAMS)
        self.tobj.get_tracks(iter(grids))
        self.tracer = Tracer(self.tobj, persist=False)
        self.tracer.color_stack = [self.tracer.color_stack[0]]

    def tearDown(self):
        pass

    def test_create_colors(self):
        colors = self.tracer.create_colors()
        self.assertTrue("blue" in colors)
        self.assertFalse("black" in colors)

    def test_update(self):
        current1 = self.tracer.current
        self.tracer.update(0)
        current2 = self.tracer.current
        self.assertEqual(current1, None)
        np.testing.assert_array_equal(current2['area'],
                                      self.tobj.tracks.loc[0]['area'])

    def test_plot(self):
        self.tracer.update(2)
        fig = plt.figure()
        lines1 = plt.gca().lines
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
        self.tracer.plot(ax)
        lines2 = plt.gca().lines
        self.assertTrue(len(lines1) == 0)
        self.assertTrue(len(lines2) > 0)


if __name__ == "__main__":
    unittest.main()
