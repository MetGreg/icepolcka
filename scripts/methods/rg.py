"""Interpolates radar data on a polar/spherical grid to a Cartesian grid.

Works for real DWD radar data as well as for simulated radar data, after the
radarfilter (which transforms original Cartesian CR-SIM data to polar
coordinates) was applied to CR-SIM.

The target Cartesian grid is exactly the WRF/CR-SIM grid in lon/lat. Heights
are defined up to 15 km in 100 m steps. The interpolation uses a nearest
neighbor interpolation.

Expects four files within the working directory. Two txt files containing
lists of radar filenames and corresponding time stamps that are to be
processed by this script. A third txt file that contains the file path to a
WRF data file that contains the lon/lat grid. And a configuration yaml file.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils.handles import WRFDataHandler, RFDataHandler, \
    DWDDataHandler
from icepolcka_utils.projection import data_to_cart, geo_to_cart, \
    spherical_to_cart
from icepolcka_utils.utils import load_config


# Settings not defined by the configuration file
# DWD variables as keys, corresponding CR-SIM variables as values
VARIABLES = {'DBZH': "Zhh", 'Zhh_corr': "Zhh_corr", 'ZDR': "Zdr",
             'Zdr_corr': "Zdr_corr", 'LDR': "LDRh", 'RHOHV': "RHOhv",
             'KDP': "Kdp", 'AH': "Ah", 'ADP': "Adp"}


def get_data_base(cfg):
    """Get data base

    Some other settings (microphysics, radar name) depend on the source of the
    data (DWD or MODEL). This function returns the corresponding settings. The
    input configuration dictionary must contain all keywords necessary.

    For an explanation on how to use the configuration file, see the README
    file.

    Args:
        cfg (dict): Configuration dictionary.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        (int, str)
            4) WRF ID of microphysics scheme.
            5) Radar name.
    """
    print("Getting data base")
    if cfg['source'] == "DWD":
        mp = None
        radar = "Isen"
    elif cfg['source'] == "MODEL":
        mp = cfg['mp']
        radar = cfg['radar']
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    return mp, radar


def get_coords():
    """Get grid coordinates

    Gets the grid coordinates from a WRF file. The name of the file must be
    given in a txt file called 'wrf_file.txt' in the same subdirectory.

    """
    print("Getting Coordinates")
    with open("wrf_file.txt", "r") as file_handle:
        file_path = file_handle.readlines()[0]
    grid_ds = WRFDataHandler.load_data(file_path.strip())
    return grid_ds['XLONG'][0].values, grid_ds['XLAT'][0].values


def get_files():
    """Get the filenames

    The file names and times of the radar data are read from the txt files
    'filenames.txt' and 'filetimes.txt'.

    Returns:
        (list, list):
            1) List of data file names.
            2) List of corresponding time stamps [UTC]

    """
    print("Getting files")
    with open("filenames.txt", "r") as file_handle:
        names = file_handle.readlines()
    with open("filetimes.txt", "r") as file_handle:
        times = file_handle.readlines()
    return names, times


def get_variables(source):
    """Get variable names

    Variable names differ between DWD and MODEL data. This function returns
    the corresponding variable names.

    Args:
        source (str): Whether 'DWD' or 'MODEL' data is processed.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        list:
            Variable names of given input data source.

    """
    print("Getting variables")
    if source == "DWD":
        variables = list(VARIABLES.keys())
    elif source == "MODEL":
        variables = list(VARIABLES.values())
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    return variables


def get_target_cart(lons, lats, heights, site):
    """Get target grid

    Given a 2D array of longitudes, a 2D array of latitudes and a 1D height
    array, this function returns one 4D grid array: (z, x, y, coords)
    where coords refers to a x/y/z tuple. x, y and z are the Cartesian
    coordinates corresponding to the input longitudes, latitudes and heights.
    The Cartesian grid origin is at radar site.

    Args:
        lons (numpy.ndarray): 2D array containing the longitude coordinates for
            each surface grid point of the target grid.
        lats (numpy.ndarray): 2D array containing the latitude coordinates for
            each surface grid point of the target grid.
        heights (numpy.ndarray): 1D array containing the height coordinates
            of the target grid.
        site (tuple or list): Longitude, Latitude, Height coordinates of radar
            site.

    Returns:
        (numpy.ndarray, SpatialReference):
            1) Array of the Cartesian coordinates of the target grid.
            2) The projection that corresponds to the Cartesian coordinates.

    """
    print("Getting target Cartesian grid")
    trg_geo = create_trg_grid(lons, lats, heights)
    trg_cart, trg_proj = geo_to_cart(trg_geo, origin=site)
    return trg_cart, trg_proj


def create_trg_grid(lons, lats, heights):
    """Creates the target grid

    Given a 2D array of longitudes, a 2D array of latitudes and a 1D height
    array, this function returns one 4D grid array: (height, lons, lats, coords)
    where coords refers to a lon/lat/alt tuple.

    Args:
        lons (numpy.ndarray: 2D array containing the longitude coordinates for
            each surface grid point of the target grid.
        lats (numpy.ndarray): 2D array containing the latitude coordinates for
            each surface grid point of the target grid.
        heights (numpy.ndarray): 1D array containing the height coordinates
            of the target grid.

    Returns:
        numpy.ndarray:
            4D array of the target grid in the format of (height, lons, lats,
            coords) where coords refers to a lon/lat/alt tuple.

    """
    print("Creating target grid")
    coords = np.concatenate((lons[..., np.newaxis], lats[..., np.newaxis]),
                            axis=-1)
    grid = np.empty((len(heights), len(lons), len(lons[0]), 3))
    grid[:, :, :, :2] = np.tile(coords, (len(heights), 1, 1, 1))
    heights_new = np.repeat(heights[:, np.newaxis, np.newaxis], len(lons),
                            axis=1)
    heights_new = np.repeat(heights_new, len(lons[0]), axis=2)
    grid[:, :, :, 2] = heights_new
    return grid


def load_data(filename, source):
    """Load data

    The loading function depends on whether 'DWD' or 'MODEL' data is
    processed. This function utilizes the correct loading function, depending on
    the data source.

    Args:
        filename (str): Name of data file.
        source (str): Whether 'DWD' or 'MODEL' data is being processed.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    """
    if source == "DWD":
        handler = DWDDataHandler()
        ds = handler.load_data(filename.strip())
    elif source == "MODEL":
        ds = RFDataHandler.load_data(filename.strip())
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    return ds


def get_src_coords(source, variables, data_cart, ds, site, src, src_cart=None):
    """Get source coordinates

    Model and radar data have different file formats. There are two functions to
    get source coordinates: get_rf_src_coords and get_dwd_src_coords. This
    function executes the corresponding function, depending on the data that
    is processed.

    Args:
        source (str): Whether 'DWD' or 'MODEL' data is processed.
        variables (list): List of variable names.
        data_cart (dict): Container for the interpolated data. One entry for
            each variable.
        ds (xarray.core.dataset.Dataset, or dict): Dataset containing the
            data and corresponding coordinates.
        site (list or tuple): Radar site coordinates.
        src (dict): Container for source coordinates. One entry for each
            variable.
        src_cart (None or numpy.ndarray): Source coordinates, if known.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        (dict, numpy.ndarray, dict):
            1) Dictionary containing the source coordinates for each variable.
            2) Array of source coordinates of latest variable.
            3) Dictionary containing the interpolated data for each variable.

    """
    if source == "DWD":
        src, data_cart = get_dwd_src_coords(ds, variables)
    elif source == "MODEL":
        for var in variables:
            src_cart, data_cart[var] = get_rf_src_coords(ds, site, var,
                                                         src_cart)
            src[var] = src_cart
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    return src, src_cart, data_cart


def get_rf_src_coords(ds, site, var, xyz=None):
    """Get src coordinates of radar filter data

    Radar filter data is simulated radar data in a spherical data format
    (azimuth, elevation, range). This function calculates the corresponding
    source coordinates in a Cartesian grid with an origin at the radar site.
    Also, the corresponding data points are returned as a 1D numpy array. This
    is done for each of the given variable names.

    If the Cartesian source coordinates are given already as an input,
    only the corresponding data for each of the grid points is returned.

    Args:
        ds (xarray.core.dataset.Dataset): Dataset that contains data and
            corresponding spherical coordinates.
        site (tuple or list): Longitude, Latitude, Height coordinates of radar
            site.
        var (str): Variable name.
        xyz (numpy.ndarray or None): If known, Cartesian source coordinates as
            an array in the format of (len(data), 3): x,y,z coordinates for
            each of the data points.

    Returns:
        (numpy.ndarray, dict):
            1) Array of the corresponding Cartesian coordinates
            2) Dictionary containing a 1D data for each variable corresponding
                to the source coordinates.

    """
    data = np.array([])

    # If source coordinates are given, just fill the data arrays with
    # corresponding data
    if xyz is not None:
        for ele in ds['elev'].values:
            array = ds[var].loc[(dict(elev=ele))]
            data = np.append(data, array.values.ravel())

    # If not, calculate the Cartesian source coordinates and stack them to
    # one source coordinates array. Get the corresponding data points and
    # return it in an array of the same format.
    else:
        xyz = np.array([]).reshape((-1, 3))
        for ele in ds['elev'].values:  # Do this for each elevation
            array = ds.loc[(dict(elev=ele))]
            r = array.range.values
            az = array.azim.values
            r_mesh, az_mesh = np.meshgrid(r, az)  # Calculations need a mesh
            elv = np.full(r_mesh.shape, array.elev)
            xyz_, proj = spherical_to_cart(r_mesh, az_mesh, elv, site)
            xyz = np.vstack((xyz, xyz_.reshape((-1, 3))))
            data = np.append(data, array[var].values.ravel())
    return xyz, data


def get_dwd_src_coords(ds_dict, variables):
    """Get src coordinates of dwd volume data

    DWD volume data is simulated radar data in a spherical data format (
    azimuth, elevation, range). This function calculates the corresponding
    source coordinates in a Cartesian grid with an origin at the radar site.
    Also, the corresponding data points are returned in a numpy array of the
    same format. This is done for each of the given variable names.

    This function is doing basically the same as get_rf_src_coords and just
    treats the calculation a little differently due to the different data
    file format. However, this function does always calculates the
    Cartesian source coordinates (and does not accept the source coordinates
    as an input to skip this and return only the corresponding data) because
    DWD measurements have slightly different azimuth/elevation values for
    each measurements. This means the source coordinates are changing between
    each measurements and have to be calculated each time.

    Args:
        ds_dict (dict): Dictionary containing a dataset for each variable.
        variables (list): List of variables to be considered.

    Returns:
        (dict, dict):
            1) Dictionary of source coordinates for each variable.
            1) Dictionary of corresponding data points for each variable

    """
    data_dict = {}
    xyz_dict = {}
    site_coords = ds_dict['site_coords']

    # Loop through all variables in data set
    for var, ds in ds_dict.items():

        # Only consider variables in variable list
        if var not in variables:
            continue

        # Loop through all elevations, calc source coordinates and stack
        # corresponding output arrays (source coordinates and data array)
        xyz, data = np.array([]).reshape((-1, 3)), np.array([])
        for ele, array in ds.items():
            r = array.range.values
            az = array.azimuth.values
            r_mesh, az_mesh = np.meshgrid(r, az)
            elv = np.full(r_mesh.shape, array.elevation)
            xyz_, proj = spherical_to_cart(r_mesh, az_mesh, elv, site_coords)
            xyz = np.vstack((xyz, xyz_.reshape((-1, 3))))
            data = np.append(data, array.values.ravel())
        data_dict[var] = data
        xyz_dict[var] = xyz
    return xyz_dict, data_dict


def data_to_grid(src, data_cart, trg_cart, itp, radar, mask):
    """Interpolate data to grid

    This function calls the interpolation method for each variable and reshapes
    the output array into a 3D target grid array. The interpolation takes a
    long time, when the mapping function (itp) is None. When the source and
    target grids stay the same, the mapping must be done only once and then the
    itp should be given to this function as an argument, which speeds up the
    interpolation by a lot.

    All variables that are not 'Zhh' or 'Zhh_corr' are masked outside the
    Mira-35 range. Zhh and Zhh_corr are kept only for the Isen radar because
    there these variables are needed over the whole domain for cell tracking.

    Args:
        src (dict): Dictionary containing the source coordinates of the
            variables.
        data_cart (dict): Dictionary containing the data values for each
            variable corresponding to the source coordinates.
        trg_cart (numpy.ndarray): Target grid coordinates. Shape (z, y, x, 3).
        itp (None or wrl.ipol.Nearest): Mapping function that maps source to
            target coordinates.
        radar (str): Radar name.
        mask (numpy.ndarray): Distance mask. True for all grid boxes outside of
            the Mira-35 range.

    Returns:
        (dict, wrl.ipol.Nearest):
            1) Dictionary containing the interpolated data array for each
                variable.
            2) Mapping function that maps source to target coordinates.

    """
    data = {}
    for var in src.keys():
        data_int, itp = data_to_cart(data_cart[var], src[var],
                                     trg_cart.reshape((-1, 3)), itp=itp)
        data[var] = data_int.reshape(trg_cart.shape[:-1])

        if not (var in ["Zhh", "Zhh_corr", "DBZH"] and radar == "Isen"):
            data[var] = np.where(~mask, data[var], np.nan)
    return data, itp


def make_folder(output, mp, radar, time, source):
    """Make output folder

    Given a folder, this function creates subdirectories according to radar,
    mp-scheme and time.

    Args:
        output (str): Path at which the output folder is created.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Name of radar.
        time (datetime.datetime). Time of data step [UTC].
        source (str): Whether 'DWD' or 'MODEL' data is being processed.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        (str):
            Path to output folder.

    """
    date = time.date()
    time_str = dt.datetime.strftime(time, "%H%M%S")
    if source == "DWD":
        output_folder = output + os.sep + "DWD" + os.sep
    elif source == "MODEL":
        output_folder = output + os.sep + "MODEL" + os.sep + "MP" + str(mp) \
                        + os.sep + radar + os.sep
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    output_folder = output_folder + os.sep + str(date.year) + os.sep \
        + f"{date.month:02d}" + os.sep + f"{date.day:02d}" + os.sep
    try:
        os.makedirs(output_folder)
    except FileExistsError:
        pass
    filename = output_folder + time_str + ".nc"
    return filename


def save(ds, time, mp, radar, lons, lats, heights, source, vert_res, z_min,
         z_max, output):
    """Save data to netcdf file

    Args:
        ds (dict): Dataset to be saved.
        mp (int): WRF ID of microphysics scheme.
        time (datetime.datetime): Time of time step [UTC].
        radar (str): Radar name.
        lons (numpy.ndarray): 2D array containing the longitude coordinates.
        lats (numpy.ndarray): 2D array containing the latitude coordinates.
        heights (numpy.ndarray): 1D array containing the height coordinates.
        source (str): Whether 'DWD' or 'MODEL' data is being processed.
        vert_res (int): Vertical resolution of grid.
        z_min (int): Minimum height of grid [m].
        z_max (int): Maximum height of grid [m].
        output (str): Output file name.

    """
    time_str = str(dt.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S"))
    data_dict = {}
    for var, var_data in ds.items():
        if var == "DBZH":
            var = "Zhh_corr"  # DWD data is naturally attenuated
        if var == "ZDR":
            var = "Zdr_corr"
        data_dict[var] = (["height", "y", "x"], var_data)
    ds = xr.Dataset(data_dict,
                    coords={
                        'lon': (["y", "x"], lons),
                        'lat': (["y", "x"], lats),
                        'height': heights
                        })
    ds.attrs['source'] = source
    ds.attrs['time'] = time_str
    ds.attrs['vert_res'] = vert_res
    ds.attrs['z_min'] = z_min
    ds.attrs['z_max'] = z_max
    if radar is not None:
        ds.attrs['radar'] = radar
    if mp is not None:
        ds.attrs['MP_PHYSICS'] = mp
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in ds.variables}
    ds.to_netcdf(output, encoding=encoding)


def main():
    print("Starting main")
    cfg = load_config('job_config.yaml')
    mp, radar = get_data_base(cfg)
    lons, lats = get_coords()
    filenames, filetimes = get_files()
    variables = get_variables(cfg['source'])
    src_cart, itp, data_cart, src = None, None, {}, {}
    heights = np.arange(cfg['cart_grid']['z_min'], cfg['cart_grid']['z_max']
                        + cfg['cart_grid']['vert_res']/2,
                        cfg['cart_grid']['vert_res'])
    trg_cart, proj_cart = get_target_cart(lons, lats, heights,
                                          cfg['sites'][radar])

    mask = np.load(cfg['masks']['Distance'])
    print("Looping through all time steps")
    for i in range(len(filenames)):
        print(filenames[i].strip())
        ds = load_data(filenames[i], cfg['source'])
        time = filetimes[i].strip()
        time = dt.datetime.strptime(time, "%Y-%m-%d_%H%M%S")
        src, src_cart, data_cart = get_src_coords(cfg['source'], variables,
                                                  data_cart, ds,
                                                  cfg['sites'][radar], src,
                                                  src_cart)
        data, itp = data_to_grid(src, data_cart, trg_cart, itp, radar, mask)
        if cfg['source'] == "DWD":
            itp = None
        output_file = make_folder(cfg['data']['RG'], mp, radar, time,
                                  cfg['source'])
        save(data, time, mp, radar, lons, lats, heights, cfg['source'],
             cfg['cart_grid']['vert_res'], cfg['cart_grid']['z_min'],
             cfg['cart_grid']['z_max'], output_file)


if __name__ == "__main__":
    main()
