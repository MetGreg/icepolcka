"""Cartesian grid calculations

This module contains all functions related to Cartesian grids, e.g. creating a Cartesian grid, or
calculating the shift between data on a Cartesian grid. Furthermore, this module includes all
function and classes related to PyArtGrid calculations and transformations.


"""
import datetime as dt

import pyart
import pytz
import numpy as np

from tint import grid_utils


class PyArtGrid(pyart.core.grid.Grid):
    """PyArtGrid

    A class for storing rectilinear gridded radar data in Cartesian coordinate.

    Most of the code of this class is taken from the PyArtGrid https://github.com/ARM-DOE/pyart

    Only the methods we need for our purposes are implemented and at some points modified to our
    needs.

    Attributes:
        time (dict): Time of the grid in UTC. Needs a 'data' and a 'units' key. The data must be
            [timestamp in seconds] since some starting datetime.
        fields (dict): Data fields. Usually reflectivity, but more fields are also possible. Each
            field needs the name as the key and a dict as value, containing a 'data' entry with the
            data as a masked array.
        x (dict): Distance [m] from the grid origin along the x-axis for each grid point along this
            axis. The distances must be provided as a list associated to a 'data' key.
        y (dict): Distance [m] from the grid origin along the y-axis for each grid point along this
            axis. The distances must be provided as a 1D-list associated to a 'data' key.
        z (dict): Distance [m] from the grid origin along the z-axis for each grid point along this
            axis. The distances must be provided as a list associated to a 'data' key.
        grid_size (~numpy.ndarray): Grid resolution in (z, y, x) dimension.

    Args:
        time (dict): Time of the grid in UTC. Needs a 'data' and a 'units' key. The data must be
            [timestamp in seconds] since some starting datetime.
        fields (dict): Data fields. Usually reflectivity, but more fields are also possible. Each
            field needs the name as the key and a dict as value, containing a 'data' entry with the
            data as a masked array.
        grid (dict): Distance [m] from the grid origin along x, y, or z axis. The distances must
            be provided as a list associated to a 'data' key.
        coords (dict): Dictionary containing 'lon' and 'lat' coordinates.

    """
    def __init__(self, time, fields, grid, coords):
        super().__init__(time, fields, {}, {}, {}, {}, grid['x'], grid['y'], grid['z'])
        self.time = time
        self.fields = fields
        self.x = grid['x']
        self.y = grid['y']
        self.z = grid['z']
        self.coords = coords
        self.grid_size = grid_utils.get_grid_size(self)

    def extract_grid_data(self, field, grid_size, params):
        """Get grid frame and raw data slice

        Returns filtered grid frame and raw grid slice at global shift altitude. The filtered grid
        frame is a mask where 0 is filtered and 1 is not filtered.

        Args:
            field (str): Name of the data field.
            grid_size (~numpy.ndarray): Array of (z, y, x) grid size.
            params (dict): Tracking parameters.

        Returns:
            (~numpy.ndarray, ~numpy.ndarray):
                1) Raw grid slice at global shift altitude
                2) Filtered frame where small echoes are filtered out

        """
        min_size = params['MIN_SIZE'] / np.prod(grid_size[1:]/1000)
        masked = self.fields[field]['data']
        masked.data[masked.data == masked.fill_value] = 5
        masked.data[np.isnan(masked.data)] = 5
        gs_alt = params['GS_ALT']
        raw = masked.data[self.get_grid_alt(gs_alt), :, :]
        frame = grid_utils.get_filtered_frame(masked.data, min_size, params['FIELD_THRESH'])
        return raw, frame

    def parse_grid_datetime(self):
        """Obtains datetime object from PyArtGrid object

        Returns:
            ~datetime.datetime:
                Grid time in UTC.

        """
        time = dt.datetime.utcfromtimestamp(self.time['data'][0])
        time = time.replace(tzinfo=pytz.utc)
        return time

    def get_grid_alt(self, alt_meters):
        """Returns z-index closest to alt_meters

        Args:
            alt_meters (int): Height to which the z-index shall be returned [m].

        Returns:
            int:
                z-index closest to alt_meters input.

        """
        try:
            z_index = np.int(np.round((alt_meters - self.z['data'][0]) / self.grid_size[0]))
            max_z_index = self.z['data'].shape[0] - 1
            if z_index > max_z_index:
                return max_z_index
            return z_index
        except ValueError:
            return 0


def create_column(coords, heights):
    """Create a column of coordinates at height steps

    Creates a column of coordinates at each of the input height steps above the input coordinates.
    The input coordinates are expected to be 2D x/y-coordinates.

    Args:
        coords (~numpy.ndarray): Coordinates above which the column shall be defined.
        heights (~numpy.ndarray): 1D array of height levels.

    Returns:
        ~numpy.ndarray:
            Numpy array of shape (len(heights), 3) representing x/y/height coordinates at each
            height.

    """
    grid = np.empty((len(heights), 3))
    grid[:, :2] = np.tile(coords, (len(heights), 1))
    grid[:, 2] = heights
    return grid


def get_pyart_grid(grid_ds, mask=None, var="Zhh_corr"):
    """Get PyArtGrid

    Create a PyArtGrid from the input data.

    Args:
        grid_ds (~xarray.Dataset): Regular grid data.
        mask (~numpy.ndarray): Mask to apply on the RegularGrid. False, if a data point is not
            considered (masked).
        var (str): Field variable name. Defaults to 'Zhh_corr'.

    Returns:
        PyArtGrid:
            PyArtGrid object corresponding to the regular grid data.

    """
    if mask is None:
        mask = np.ones(grid_ds[var].shape)
    time = dt.datetime.strptime(str(grid_ds.attrs['time']),
                                "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
    x_grid = np.arange(0, 360 * 400, 400)
    y_grid = np.arange(0, 360 * 400, 400)
    z_grid = np.arange(grid_ds.z_min, grid_ds.z_max + grid_ds.vert_res, grid_ds.vert_res)
    lons = grid_ds['lon']
    lats = grid_ds['lat']
    data = np.where(mask, grid_ds[var].values, np.nan)
    data_masked = np.ma.masked_where((data < 5) | (np.isnan(data)), data)

    # Define time, and grid dictionaries for the PyArtGrid object
    x_grid = {'data': x_grid}
    y_grid = {'data': y_grid}
    z_grid = {'data': z_grid}
    time = {'data': np.array([dt.datetime.timestamp(time)]), 'units': "seconds since 1970-01-01"}
    fields = {'reflectivity': {'data': data_masked}}
    grid = {'x': x_grid, 'y': y_grid, 'z': z_grid}
    grid = PyArtGrid(time, fields, grid, {'lon': lons.values, 'lat': lats.values})
    return grid
