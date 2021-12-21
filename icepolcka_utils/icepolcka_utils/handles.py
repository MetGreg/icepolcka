"""Data handles for data base

All data base classes need a corresponding data handle class that handles
the data, for example by loading them into a xarray. This module contains
all these data handles.

"""
import h5py
import os
import pickle
import datetime as dt
import numpy as np
import xarray as xr
from netCDF4 import Dataset
from scipy import ndimage

from icepolcka_utils.utils import get_mean_angle


class DataHandler(object):
    """Data Handler abstract class

    This is the abstract super class of all DataHandler subclasses. The
    purpose of this class is to document all common methods.

    The following methods are available to all subclasses:

    - :meth:`load_data`:
        Loads the data into a xarray.

    """
    @staticmethod
    def load_data(data_file):
        """Read in data

        Reads the data from the data file into a xarray.

        Args:
            data_file (str): Path to data file to be loaded.

        Returns:
            :xarray:`xarray.Dataset <Dataset.html>`:
                Xarray containing the data.

        """
        raise NotImplementedError


class WRFDataHandler(DataHandler):
    """WRF data handler

    Class to handle WRF data. For documentation of general DataHandler methods,
    see super class.

    """
    def __init__(self):
        pass

    @staticmethod
    def load_data(data_file):
        df = xr.open_dataset(data_file)
        times = [dt.datetime.strptime(str(date), "b'%Y-%m-%d_%H:%M:%S'")
                 for date in df['Times'].values]
        df['Time'] = times
        df.close()
        return df


class CRSIMDataHandler(DataHandler):
    """CR-SIM data handler

    Class to handle CR-SIM data. For documentation of general DataHandler
    methods, see super class.

    """
    def __init__(self):
        pass

    @staticmethod
    def load_data(data_file):
        ds = xr.open_dataset(data_file)
        return ds


class RFDataHandler(DataHandler):
    """Radar filter data handler

    Class to handle radar filter data. For documentation of general DataHandler
    methods, see mother class.

    """
    def __init__(self):
        pass

    @staticmethod
    def load_data(data_file):
        ds = xr.open_dataset(data_file)
        return ds


class RGDataHandler(DataHandler):
    """Regular grid data handler

    Class to handle regular grid data. For documentation of general DataHandler
    methods, see mother class.

    """
    def __init__(self):
        pass

    @staticmethod
    def load_data(data_file):
        ds = xr.open_dataset(data_file)
        return ds


class TracksDataHandler(object):
    """Cell tracks data handler

    Class to handle cell tracks data. For documentation of general DataHandler
    methods, see mother class.

    """
    def __init__(self):
        pass

    @staticmethod
    def load_data(data_file):
        with open(data_file, "rb") as f:
            pkl = pickle.load(f)
        ds = pickle.loads(pkl)
        return ds


class DWDDataHandler(DataHandler):
    """DWD volume data handler

    Class to handle DWD volume data. Used to load data. For documentation of
    general DataHandler methods, see mother class.

    The following extra methods are available:

    - :meth:`gain_to_data`:
        Transform gain and offset to actual data.

    """
    def __init__(self):
        pass

    def load_data(self, file_path):
        """Read in data

        Reads the data from the data file into a xarray.

        Args:
            file_path (str): Path to data file.

        Returns:
            dict:
                List containing a xarray Dataset for each variable.

        """
        ncf = Dataset(file_path)
        quantities = ["DBZH", "ZDR", "RHOHV", "KDP"]
        data_arrays = {}
        elevations = []
        for var in ncf.groups:
            nc_var = ncf[var]
            quantity = nc_var['dataset1']['data1']['what'].quantity
            if quantity not in quantities:
                continue
            data = self.gain_to_data(nc_var['dataset1']['data1'])
            az = nc_var['dataset1']['how'].startazA
            elev = nc_var['dataset1']['where'].elangle
            time = dt.datetime.strptime(nc_var['what'].date
                                        + nc_var['what'].time, "%Y%m%d%H%M%S")
            rhgt = nc_var['where'].height
            rlon = nc_var['where'].lon
            rlat = nc_var['where'].lat
            rstart = nc_var['dataset1']['where'].rstart
            rscale = nc_var['dataset1']['where'].rscale
            nbins = nc_var['dataset1']['where'].nbins
            r = np.arange(rstart, rscale*nbins, rscale)
            da = xr.DataArray(data, coords=[az, r], dims=["azimuth", "range"],
                              attrs={'elevation': elev})
            if quantity not in data_arrays.keys():
                data_arrays[quantity] = {}
            if elev not in elevations:
                elevations.append(elev)
            data_arrays[quantity][elev] = da

        # Save attributes
        final = {
            'time': time,
            'site_coords': (rlon, rlat, rhgt)
            }
        for var in quantities:
            final[var] = {}
            for elv in elevations:
                final[var][np.round(elv, 2)] = data_arrays[var][elv]

        # Close data file
        ncf.close()
        return final

    @staticmethod
    def gain_to_data(pd_data):
        """Transform gain and offset to actual data values

        pd_data (netCDF4.Group): h5py container with offset, gain and data.

        Returns:
            numpy.ndarray:
                Transformed data.

        """
        zhoffset = pd_data['what'].offset
        zhgain = pd_data['what'].gain
        reflect = np.array(pd_data['data'])
        reflect = np.ma.masked_less_equal(reflect, 0)
        reflect = np.ma.masked_invalid(reflect)
        reflect = zhoffset + reflect*zhgain
        return reflect


class MiraDataHandler(DataHandler):
    """Mira-35 data handler

    Class to handle Mira-35 data. Used to load data from a data file and to
    find all Rhi-sweeps or PPI-sweeps within this file.

    For documentation of general DataHandler methods, see mother class.

    The following extra methods are available:

        - :meth:`get_site_coords`:
            Gets the site coords of the radar.
        - :meth:`find_rhi_sweeps`:
            Finds the rhi sweeps within the data.

    Args:
        north_offset (float):  Offset from radar 0 degree to north direction.

    """
    def __init__(self, north_offset=157.3):
        self.north_offset = north_offset

    def load_data(self, dataset, start_time=None, end_time=None):
        """Read in data

        Reads the data from the file into a xarray.

        Args:
            dataset (dict): Dataset containing an mmclx-file and/or the
                corresponding nc-file.
            start_time (datetime.datetime): Start time [UTC] of data to be
                loaded.
            end_time (datetime.datetime): End time [UTC] of data to be loaded.

        Raises:
            AssertionError: If no data could be opened.

        Returns:
            :xarray:`xarray.Dataset <Dataset.html>`:
                Xarray containing the data.

        """
        try:
            ds_mmclx = xr.open_dataset(dataset['mmclx_file'], decode_cf=False)
            ds_mmclx['time'].attrs['units'] = "seconds since 1970-01-01"
            ds_mmclx = xr.decode_cf(ds_mmclx)
            ds = ds_mmclx
        except ValueError:
            pass

        try:
            ds_nc = xr.open_dataset(dataset['nc_file'], decode_cf=False)
            ds_nc['time'].attrs['units'] = "seconds since 1970-01-01"
            ds_nc = xr.decode_cf(ds_nc)
            ds = ds_nc
        except ValueError:
            pass

        # If the files within the ds_dictionary do not exist, raise error
        if "ds" not in locals():
            raise AssertionError("Requested Mira data could not be found.")

        # Get site and reflectivity
        lon, lat, alt = self.get_site_coords(ds)
        ldr = ds['LDRg']
        reflect = 10 * np.log10(ds['Zg'][:])
        snr = 10*np.log10(ds['SNRg'][:])
        reflect.attrs['units'] = "dBZ"
        snr.attrs['units'] = "dB"

        # Create dataset
        ds_new = xr.Dataset({
            'az': (ds['azi'] - self.north_offset) % 360,
            'azv': ds['aziv'],
            'elv': ds['elv'],
            'elvv': ds['elvv'],
            'ldr': ldr,
            'snr': snr,
            'r': ds['range'],
            'times': ds['time'],
            'reflectivity': reflect
            },
            attrs={'institution': ds.institution,
                   'site_coords': (lon, lat, alt)})

        ds_new = ds_new.sel(time=slice(start_time, end_time))
        ds.close()
        return ds_new

    @staticmethod
    def get_site_coords(ds):
        """Get site coordinates

        Reads the site coordinates. For about three weeks in June/July 2019,
        the site coordinates within the data was wrong (it was from
        Hamburg). That's why, if the site coords correspond to the Hamburg
        coordinates, it will be hard coded to the LMU location.

        Args:
            ds (:xarray:`xarray.Dataset <Dataset.html>`): Opened data.

        Returns:
            (float, float, float):
                1) Longitude of site.
                2) Latitude of site.
                3) Altitude of site [m].

        """
        # If site coords are not in standard format - put it to nan
        try:
            lon = float(ds.Longitude[:-2])
        except ValueError:
            lon = np.nan
        try:
            lat = float(ds.Latitude[:-2])
        except ValueError:
            lat = np.nan
        try:
            alt = float(ds.Altitude[:-2])
        except ValueError:
            alt = np.nan

        # For some time, Metek had the wrong location configured
        if ds.location == "Elmshorn":
            lon = 11.573550
            lat = 48.148021
            alt = 541

        return lon, lat, alt

    @staticmethod
    def find_ppi_sweeps(data, n=30):
        """Find all PPI sweeps in data

        Finds the PPI scans by azimuth speed. When the azimuth speed is
        between 0.5 and 5 °/s, while the elevation speed is zero, is assumed to
        be an PPI scan. There must also be at least 'n' data points in a row to
        be treated as a PPI-scan. Furthermore, the elevation must be lower than
        90° to count as a PPI scan.

        Args:
            data (:xarray:`xarray.Dataset <Dataset.html>`): Xarray containing
                mira radar data.
            n (int): Number of data points in a row to be treated as a PPI
                scan. Defaults to 30.

        Returns:
           list:
            List with slices that correspond to the PPI scans within the data.

        """
        trig = ((abs(data.azv) > 0.5) & (abs(data.azv) < 5.0)
                & (abs(data.elvv) < 0.1) & (abs(data.elv) < 90))
        labels, num = ndimage.label(trig)
        sweeps = ndimage.find_objects(labels)
        sweeps = [s[0] for s in sweeps if s[0].stop - s[0].start > n]
        return sweeps

    @staticmethod
    def find_rhi_sweeps(data, n=30):
        """Find all RHI sweeps in data

        Finds the RHI scans by elevation speed. When the elevation speed is
        between 0.5 and 5 °/s, while the azimuth speed is zero, it is assumed
        to be an RHI scan. There must also be at least 'n' data points in a row
        to be treated as a RHI-scan.

        Args:
            data (:xarray:`xarray.Dataset <Dataset.html>`): Xarray containing
                Mira-35 radar data.
            n (int): Number of data points in a row to be treated as a RHI
                scan. Defaults to 30.

        Returns:
           list:
                List with slices that correspond to the RHI scans within the
                data.

        """
        trig = ((data.elvv > 0.5) & (data.elvv < 5.0) & (data.azv > -0.1)
                & (data.azv < 0.1))
        labels, num = ndimage.label(trig)
        sweeps = ndimage.find_objects(labels)
        sweeps = [s[0] for s in sweeps if s[0].stop - s[0].start > n]
        return sweeps


class PoldiDataHandler(DataHandler):
    """Poldi data handler

    Class to handle Poldirad data. For documentation of general DataHandler
    methods, see mother class.

    The following extra methods are available:

            - :meth:`gain_to_data`:
                Transforms gain and offset to actual data values.
            - :meth:`split_poldi_az`:
                Splits the poldirad azimuth angle strings.
            - :meth:`split_poldi_elv`:
                Splits the poldirad elevation angle strings.
            - :meth:`get_correct_datetime`:
                Gets the full datetime of each measurement.

    """
    def __init__(self):
        pass

    def load_data(self, file_name, scan=None):
        """Read in data

        Reads the data from the file into a xarray.

        Args:
            file_name (str): Name of the data file.
            scan (int): Number of scan to return, in case of multiple scans
                per file.

        Raises:
            AssertionError: If task attribute is unknown.

        Returns:
            xarray.core.dataset.Dataset:
                List of xarray datasets, one for each dataset within the file.

        """
        try:
            pd = h5py.File(file_name, "r")
        except OSError:
            print("WARNING: File cannot be opened.")
            return
        task = pd['how'].attrs['task']
        if task == "MIM" or task == "RHI":
            task = "RHI"
        elif task == "Uebersicht":
            task = "PPI"
        elif task == "HV-Volumen" or task == "Volumen":
            time_start = pd['what'].attrs['time']
            date_start = pd['what'].attrs['date']
            time_stop = pd['what'].attrs['stop']
            date_stop = pd['what'].attrs['stopdate']
            start_dt = dt.datetime.strptime(str(date_start + time_start),
                                            "%Y%m%d%H%M%S")
            stop_dt = dt.datetime.strptime(str(date_stop + time_stop),
                                           "%Y%m%d%H%M%S")
            ds = xr.Dataset({'task': task, 'time_start': start_dt,
                             'time_end': stop_dt})
            return ds
        elif task == "":
            file_split = file_name.split(os.sep)
            if "ST009" in file_split:
                task = "RHI"
            else:
                print("WARNING: File has no task attribute. Returning.")
                return
        else:
            raise AssertionError("Task attribute not known.")

        # Get site location
        rlon = pd.get("where").attrs['lon']
        rlat = pd.get("where").attrs['lat']
        rhgt = pd.get("where").attrs['height']

        # Get angles
        angles = pd.get("how").attrs['angles']
        if not angles:
            print("WARNING: No scan angle found")
            return
        angles = [float(x) for x in angles.split(",")]
        scan_angle = float(angles[0])

        # Get radar parameter for all angles
        ds_full = None
        for dataset in pd.keys():
            if dataset.find("dataset") == 0:
                pddat = pd.get(dataset)
                rstart = pddat.get("where").attrs['rstart']
                rscale = pddat.get("where").attrs['rscale']
                nbins = pddat.get("where").attrs['nbins']
                ds_angle = pddat.get("where").attrs['elangle']

                # Get elevation angles
                el_str = pddat['how'].attrs['elangles']
                elv = self.split_poldi_elv(el_str)

                # Get time
                time_start = dt.datetime.strptime(
                    str(pddat['what'].attrs['startdate']
                        + pddat['what'].attrs['starttime']),
                    "%Y%m%d%H%M%S"
                    )
                time_end = dt.datetime.strptime(
                    str(pddat['what'].attrs['stopdate']
                        + pddat['what'].attrs['stoptime']),
                    "%Y%m%d%H%M%S"
                    )

                # Get times from attribute 'aztimes', which is similar
                # to the angles, a string of the form
                # 'time_start1:time_end1,time_start2:time_end2'. The
                # corresponding start and end times for on azimuth
                # measurement are the same for the files that I looked at,
                # which is why I just choose one of them
                times = np.array(
                    [dt.datetime.strptime(x.split(":")[1], "%H%M%S.%f")
                     for x in pddat['how'].attrs['aztimes'].split(",")]
                    )
                times = self.get_correct_datetime(times, time_start,
                                                  time_end)

                # To filter correct quantity
                for data in pddat.keys():
                    pd_data = pddat[data]
                    if data.find("data") == 0:
                        if pd_data['what'].attrs['quantity'] == "DBZH":
                            reflect = self.gain_to_data(pd_data)
                            iaz, ira = reflect.shape
                        elif pd_data['what'].attrs['quantity'] == "LDR":
                            ldr = self.gain_to_data(pd_data)
                        elif pd_data['what'].attrs['quantity'] == "ZDR":
                            zdr = self.gain_to_data(pd_data)
                        elif pd_data['what'].attrs['quantity'] == "RHOHV":
                            rhohv = self.gain_to_data(pd_data)
                        elif pd_data['what'].attrs['quantity'] == "KDP":
                            kdp = self.gain_to_data(pd_data)

                # Define the range coordinate (center of bin)
                r = np.arange(
                    rstart + rscale/2, np.max((ira, nbins))*rscale, rscale
                    )

                # Define the azimuth coordinate (center of ray)
                az_str = pddat.get("how").attrs['azangles']
                az = self.split_poldi_az(az_str)

                # Check, if dimensions are valid
                if reflect.shape != (times.shape[0], r.shape[0]):
                    print("WARNING: Dimensions are not valid")
                    return

                # LDR, rhohv, kdp sometimes not available
                # create nan array in this case
                if "ldr" not in locals():
                    ldr = np.full((times.shape[0], r.shape[0]), np.nan)
                if "rhohv" not in locals():
                    rhohv = np.full((times.shape[0], r.shape[0]), np.nan)
                if "kdp" not in locals():
                    kdp = np.full((times.shape[0], r.shape[0]), np.nan)

                # Save attributes
                ds = xr.Dataset({
                    'az': xr.DataArray(
                        az, coords=[times], dims=["time"],
                        attrs={'long_name': "Azimuth angle", 'units': "deg"}
                        ),
                    'elv': xr.DataArray(
                        elv, coords=[times], dims=["time"],
                        attrs={'long_name': "Elevation angle", 'units': "deg"}
                        ),
                    'ldr': xr.DataArray(
                        ldr, coords=[times, r], dims=["time", "range"],
                        attrs={'long_name': "Linear depolarization ratio"}
                        ),
                    'r': xr.DataArray(
                        r, coords=[r], dims=["range"],
                        attrs={'long_name': "Range from Antenna to the Centre "
                                            "of each Range Gate", 'units': "m"}
                        ),
                    'times': xr.DataArray(
                        times, coords=[times], dims=["time"],
                        attrs={'long_name': "Times of measurements"}
                        ),
                    'reflectivity': xr.DataArray(
                        reflect, coords=[times, r], dims=["time", "range"],
                        attrs={'long_name': "Equivalent Radar Reflectivity "
                                            "Factor Ze of Hydrometeors",
                               'units': "dBZ"}
                        ),
                    'zdr': xr.DataArray(
                        zdr, coords=[times, r], dims=["time", "range"],
                        attrs={'long_name': "Differential Radar Reflectivity",
                               'units': "dB"}
                        ),
                    'rhohv': xr.DataArray(
                        rhohv, coords=[times, r], dims=["time", "range"],
                        attrs={'long_name': "Cross-correlation coefficient",
                               'units': ""}
                        ),
                    'kdp': xr.DataArray(
                        kdp, coords=[times, r], dims=["time", "range"],
                        attrs={'long_name': "Specific differential phase",
                               'units': "deg/km"}
                        )},
                    attrs={'institution': "DLR",
                           'site_coords': (rlon, rlat, rhgt),
                           'task': task, 'Resolution': rscale}
                    )

                # Concatenate multiple scans into one dataset
                if ds_full is None:
                    ds_full = ds
                    ds_full = ds_full.expand_dims("scan_number")
                else:
                    ds_full = xr.concat([ds_full, ds], dim="scan_number")

        ds_full = ds_full.assign_coords(
            scan_number=np.arange(ds_full.dims['scan_number'])
            )
        # If a specific scan is wanted, select it by the number
        if scan is not None:
            ds_full = ds_full.isel(scan_number=scan)
        return ds_full

    @staticmethod
    def gain_to_data(pd_data):
        """Transform gain and offset to actual data values

        pd_data (h5py.Group_): h5py container with offset, gain and data.

        Returns:
            numpy.ndarray:
                Transformed data.

        """
        zhoffset = pd_data['what'].attrs['offset']
        zhgain = pd_data['what'].attrs['gain']
        reflect = np.array(pd_data['data'])
        reflect = np.ma.masked_less_equal(reflect, 0)
        reflect = np.ma.masked_invalid(reflect)
        reflect = zhoffset + reflect*zhgain
        return reflect

    @staticmethod
    def split_poldi_az(string):
        """Split poldirad azimuth angle strings

        In the Poldirad data files, angles are often saved as one big string of
        the form: 'angle1:angle2,angle3:angle4' and so on. In this example this
        means the first measurement bin extended from angle1 to angle2,
        the second measurement bin from angle3 to angle4 and so on.

        The returned angle for each measurement bin corresponds to the
        center of the bin.

        Args:
            string (str): Poldirad string of azimuth angles of the form
                'angle1:angle2,angle3:angle4' and so on.

        Returns:
            numpy.ndarray:
                Array with the mean azimuth angle for each measurement bin.

        """
        return_list = []
        measurements = string.split(",")
        for ang in measurements:
            ang_split = ang.split(":")
            angle1 = (float(ang_split[0]) + 360) % 360
            angle2 = (float(ang_split[1]) + 360) % 360
            ang_mean = get_mean_angle(angle1, angle2)
            return_list.append(ang_mean)
        return np.array(return_list)

    @staticmethod
    def split_poldi_elv(string):
        """Split poldirad elevation angle strings

        In the Poldirad data files, angles are often saved as one big string of
        the form: 'angle1:angle2,angle3:angle4' and so on. In this example this
        means the first measurement bin extended from angle1 to angle2,
        the second measurement bin from angle3 to angle4 and so on.

        The returned angle for each measurement bin corresponds to the center
        of the bin.

        The difference to split_poldi_az is that here it is assumed that no
        jump from 360 to 0 degree happens, since this method is intended for
        elevation angles. Instead, negative angles are allowed here.

        Args:
            string (str): Poldirad string of elevation angles of the form
                'angle1:angle2,angle3:angle4' and so on.

        Returns:
            numpy.ndarray:
                Array with the mean elevation angle for each measurement bin.

        """
        return_list = []
        measurements = string.split(",")
        for ang in measurements:
            ang_split = ang.split(":")
            angle1 = float(ang_split[0])
            angle2 = float(ang_split[1])
            ang_mean = (angle1 + angle2)/2
            return_list.append(ang_mean)
        return np.array(return_list)

    @staticmethod
    def get_correct_datetime(times, start_date, end_date):
        """Get full datetime of each measurement

        Within Poldirad, only the date of the start and the stop time is saved.
        For each individual measurement, only the time (not the date) is saved.
        To obtain a full datetime object, this method checks whether there is
        a jump between the times of two measurements (which would correspond to
        a new day). If there is no such jump --> start date is added to the
        measurement time. If such a jump was recognized --> stop date is added
        from then on to each measurement time.

        The jump is found by calculating the time delta between two adjacent
        measurements. If it is greater than 1 second, a new day is assumed.

        Note:
            This method assumes that stop and start date are at maximum 1 day
            apart.

        Args:
            times (numpy.ndarray or list): Array of datetime objects [UTC] that
                correspond to the measurement times.
            start_date (datetime.datetime): Start date + time [UTC].
            end_date (datetime.datetime): End date + time [UTC].

        Returns:
            numpy.ndarray:
                List of the complete date + times [UTC] of each measurement.

        """
        new_day = False
        time_dates = []
        for ind in range(len(times)):
            if new_day:
                year = end_date.year
                month = end_date.month
                day = end_date.day
            else:
                year = start_date.year
                month = start_date.month
                day = start_date.day
            time_dates.append(dt.datetime(year, month, day, times[ind].hour,
                                          times[ind].minute, times[ind].second,
                                          times[ind].microsecond))
            if ind == len(times)-1:
                return np.array(time_dates)
            if (times[ind+1] - times[ind]).days != 0:
                new_day = True


class ResultHandle(object):
    """Handle results of database queries

    The RadarDataBase queries should not return opened datasets, as for
    large amount of data, this would waste memory. Instead, this handle
    class will be returned, which includes meta data about the returned
    datasets and only loads the data if explicitly demanded.

    The following methods are available:

        - :meth:`load`:
            Loads the data with the loader function.

    Args:
        attrs (dict): Dictionary with meta data about the dataset.
        loader(func): Function to load the data.

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
            :xarray:`xarray.Dataset <Dataset.html>` or dict:
                The dataset containing the data.

        """
        ds = self._loader()
        if ds is None:
            raise OSError("Loading failed. Do you have access to the datafile?")
        for k, v in self._attrs.items():
            ds.attrs[k] = v
        return ds
