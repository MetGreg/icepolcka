"""Tests for plots module"""
import unittest

import cartopy
import matplotlib
import numpy as np
import xarray as xr

from icepolcka_utils import plots


class PlotsTest(unittest.TestCase):
    """Tests for all functions in the plots module"""

    def test_plot_munich_creates_figure_cartopy_image_when_levels_are_given(self):
        levels = np.arange(0, 5, 1)
        img = self._prepare_img(levels=levels)
        self.assertTrue(isinstance(img, cartopy.mpl.contour.GeoContourSet))

    def test_plot_munich_creates_figure_quadmesh_image_without_levels(self):
        img = self._prepare_img()
        self.assertTrue(isinstance(img, matplotlib.collections.QuadMesh))

    def test_create_subplots_creates_figure(self):
        fig, _ = plots.create_subplots()
        self.assertTrue(isinstance(fig, matplotlib.figure.Figure))

    @staticmethod
    def _prepare_img(levels=None):
        grid = {'x_axis': False, 'y_axis': False}
        image = {'xlabel': "Test xlabel", 'ylabel': "Test ylabel", 'vmin': 0, 'vmax': 10}
        cfg = plots.PlotConfig(grid_cfg=grid, image_cfg=image)
        array = np.array([[1, 2, 3], [4, 5, 6]])
        grid = xr.Dataset(coords=dict(lon=(["y", "x"], array), lat=(["y", "x"], array)))
        img = plots.plot_munich(array, grid, cfg, levels=levels)
        return img


class PlotConfigTest(unittest.TestCase):
    """Tests for the PlotConfig class"""

    def test_plot_config_creates_correct_title_font(self):
        image = {'vmin': 1}
        fonts = {'title': 20}
        grid = {'x_axis': False}
        plot_cfg = plots.PlotConfig(image_cfg=image, fonts_cfg=fonts, grid_cfg=grid)
        self.assertEqual(plot_cfg.fonts['title'], 20)


if __name__ == "__main__":
    unittest.main()
