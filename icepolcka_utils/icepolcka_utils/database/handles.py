"""Data handles for database

This module contains all classes and functions designed to load and handle any data and data
formats used in IcePolCKa.

"""
import datetime as dt
import netCDF4
import numpy as np
import xarray as xr


class DWDDataHandler:
    """DWD volume data handler

    Class to handle DWD volume data. Used to load data.

    """

    def load_data(self, data_file):
        """Load data to a xarray

        Reads the data from the data file into a xarray.

        :param data_file: Path to data file.
        :type data_file: str

        Returns:
            dict:
                List containing a :obj:`~xarray.Dataset` for each variable from the original DWD
                data file.

        """
        ncf = netCDF4.Dataset(data_file)
        quantities = ["DBZH", "ZDR", "RHOHV", "KDP"]
        data_arrays = {}
        elevations = []
        final = None
        for var in ncf.groups:
            if ncf[var]['dataset1']['data1']['what'].quantity not in quantities:
                continue
            data = self._gain_to_data(ncf[var]['dataset1']['data1'])
            az_coord = ncf[var]['dataset1']['how'].startazA
            elev = ncf[var]['dataset1']['where'].elangle
            time = dt.datetime.strptime(ncf[var]['what'].date + ncf[var]['what'].time,
                                        "%Y%m%d%H%M%S")
            r_coord = np.arange(
                ncf[var]['dataset1']['where'].rstart,
                ncf[var]['dataset1']['where'].rscale*ncf[var]['dataset1']['where'].nbins,
                ncf[var]['dataset1']['where'].rscale
                )
            da_data = xr.DataArray(data, coords=[az_coord, r_coord], dims=["azimuth", "range"],
                                   attrs={'elevation': elev})
            if ncf[var]['dataset1']['data1']['what'].quantity not in data_arrays:
                data_arrays[ncf[var]['dataset1']['data1']['what'].quantity] = {}
            if elev not in elevations:
                elevations.append(elev)
            data_arrays[ncf[var]['dataset1']['data1']['what'].quantity][elev] = da_data

            final = {'time': time, 'site_coords': (ncf[var]['where'].lon, ncf[var]['where'].lat,
                                                   ncf[var]['where'].height)}
        for var in quantities:
            final[var] = {}
            for elv in elevations:
                final[var][np.round(elv, 2)] = data_arrays[var][elv]

        # Close data file
        ncf.close()
        return final

    @staticmethod
    def _gain_to_data(pd_data):
        zhoffset = pd_data['what'].offset
        zhgain = pd_data['what'].gain
        reflect = np.array(pd_data['data'])
        reflect = np.ma.masked_less_equal(reflect, -1)
        reflect = np.ma.masked_invalid(reflect)
        reflect = zhoffset + reflect * zhgain
        return reflect


class ResultHandle:
    """Handle object of database queries

    The RadarDataBase queries should not return opened datasets, because for large amount of data
    this would waste memory. Instead, this handle class will be returned, which includes metadata
    about the returned datasets and only loads the data if explicitly demanded.

    :param attrs: Dictionary with metadata about the dataset.
    :type attrs: dict
    :param loader: Function that is used to load the data when demanded.

    """
    def __init__(self, attrs, loader):
        self._attrs = attrs
        self._loader = loader

    def __getitem__(self, key):
        return self._attrs[key]

    def load(self):
        """Load the data

        Only when this function is called, the data is loaded.

        Returns:
            ~xarray.Dataset or dict:
                The dataset containing the data and with added attributes.

        """
        ds_loaded = self._loader()
        if isinstance(ds_loaded, dict):
            return self._load_dict(ds_loaded)
        for key, value in self._attrs.items():
            ds_loaded.attrs[key] = value
        return ds_loaded

    def _load_dict(self, ds_data):
        for key, value in self._attrs.items():
            ds_data[key] = value
        return ds_data


def load_wrf_data(data_file):
    """Load wrf data

    Next to loading the data into a xarray, the function adds a time variable with the time as
    datetime, because it is originally in bytes.

    :param data_file: Path to the data file.
    :type data_file: str

    Returns:
        ~xarray.Dataset:
            Loaded dataset.

    """
    df_wrf = xr.open_dataset(data_file)
    times = [dt.datetime.strptime(str(date), "b'%Y-%m-%d_%H:%M:%S'")
             for date in df_wrf['Times'].values]
    df_wrf['Time'] = times
    return df_wrf


def load_xarray(data_file):
    """Loads data into a xarray


    :param data_file: Path to the data file.
    :type data_file: str

    Returns:
        ~xarray.Dataset:
            Loaded dataset.

    """
    return xr.open_dataset(data_file)
