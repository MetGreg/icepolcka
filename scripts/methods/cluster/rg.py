"""Interpolates radar data on a polar/spherical grid to a Cartesian grid.

Works for real DWD radar data as well as for simulated radar data, after the radarfilter (which
transforms original Cartesian CR-SIM data to polar coordinates) was applied to CR-SIM.

The target Cartesian grid is exactly the WRF/CR-SIM grid in lon/lat. Heights are defined up to 15 km
in 100 m steps.

Expects four files within the working directory. Two txt files containing lists of radar filenames
and corresponding time stamps that are to be processed by this script. A third txt file that
contains the file path to a WRF data file that contains the lon/lat grid. And a configuration yaml
file.


"""
import os
import datetime as dt
import numpy as np
import xarray as xr
from scipy.ndimage import filters

from icepolcka_utils.database import handles
from icepolcka_utils import projection, utils

CONFIG_FILE = "job_config.yaml"
KDP_SMOOTH = 5000

# Settings not defined by the configuration file
# DWD variables as keys, corresponding CR-SIM variables as values
VARIABLES = {'DBZH': "Zhh", 'Zhh_corr': "Zhh_corr", 'ZDR': "Zdr", 'Zdr_corr': "Zdr_corr",
             'LDR': "LDRh", 'RHOHV': "RHOhv", 'KDP': "Kdp", 'AH': "Ah", 'ADP': "Adp"}


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    coords = _get_coords()
    filenames, filetimes = _get_files()
    src_cart, itp, data_cart, src = None, None, {}, {}
    trg_cart, _ = _get_target_cart(coords[0], coords[1], cfg)
    for i, _ in enumerate(filenames):
        if _check_output_exists(cfg, filetimes[i]):
            continue
        print(filenames[i])
        ds_data = _load_data(filenames[i], cfg['source'])
        ds_data = _smooth_kdp(ds_data, cfg)
        src, src_cart, data_cart = _get_src_coords(cfg, data_cart, ds_data, src, src_cart)
        data_itp, itp = _data_to_grid(src, data_cart, trg_cart, itp)
        _save(data_itp, cfg, coords, filetimes[i])

        # The DWD source coordinates are not constant, because the scans can start at slightly
        # different elevation/azimuth angles. This is why the interpolation must be done from
        # scratch --> Put mapping information (itp) to None
        if cfg['source'] == "DWD":
            itp = None


def _smooth_kdp(ds_data, cfg):
    if cfg['source'] == "DWD":
        return _smooth_kdp_dwd(ds_data)
    if cfg['source'] == "MODEL":
        return _smooth_kdp_model(ds_data)
    raise AssertionError("Configured data source not known")


def _smooth_kdp_dwd(ds_data):
    kdp_smooth_dict = {}
    for ele, array in ds_data['KDP'].items():
        r_coord = array['range'].values
        az_coord = array['azimuth'].values
        res = array['range'].values[1] - array['range'].values[0]
        size = int(KDP_SMOOTH/res)
        kdp = array.values.copy()
        kdp_smooth = _running_mean(kdp, size)
        kdp_smooth_dict[ele] = xr.DataArray(kdp_smooth, dims=("azimuth", "range"),
                                            coords=dict(azim=(['azimuth'], az_coord),
                                                        range=(['range'], r_coord)),
                                            attrs={'elevation': array.elevation})
    ds_data["Kdp"] = kdp_smooth_dict
    return ds_data


def _smooth_kdp_model(ds_data):
    res = ds_data['range'].values[1] - ds_data['range'].values[0]
    size = int(KDP_SMOOTH/res)
    kdp = ds_data["Kdp"].values.copy()
    kdp_smooth = _running_mean(kdp, size)
    ds_data["Kdp"] = (["azim", "elev", "range"], kdp_smooth)
    return ds_data


def _running_mean(kdp, size):
    # For smoothing, a running mean over 5 km is calculated. This is done with the uniform_filter1d
    # method of scipy. This method is very fast, but it does not treat NaNs very well (The whole
    # running mean is nan, when there is one missing value). That's why, this method fills the
    # missing values with interpolated values of the nearest valid values along the range axis.
    # In the end, the NaNs are reapplied, because the interpolation otherwise fills areas outside
    # the domain with values
    mask = np.isnan(kdp)
    if np.sum(~np.isnan(kdp[~mask])) == 0:  # Sometimes only missing values, then instant return
        return kdp
    kdp[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), kdp[~mask])
    kdp_smooth = filters.uniform_filter1d(kdp, size=size)
    kdp_smooth[mask] = np.nan
    return kdp_smooth


def _get_coords():
    with open("wrf_file.txt", "r", encoding="utf-8") as file_handle:
        file_path = file_handle.readlines()[0]
    grid_ds = handles.load_wrf_data(file_path.strip())
    return grid_ds['XLONG'][0].values, grid_ds['XLAT'][0].values


def _get_files():
    with open("filenames.txt", "r", encoding="utf-8") as file_handle:
        names = file_handle.readlines()
    with open("filetimes.txt", "r", encoding="utf-8") as file_handle:
        times = file_handle.readlines()
    return names, times


def _get_target_cart(lons, lats, cfg):
    heights = _get_heights(cfg)
    trg_geo = _create_trg_grid(lons, lats, heights)
    trg_cart, trg_proj = projection.geo_to_cart(trg_geo, origin=cfg['sites'][cfg['radar']])
    return trg_cart, trg_proj


def _get_heights(cfg):
    heights = np.arange(cfg['cart_grid']['z_min'], cfg['cart_grid']['z_max']
                        + cfg['cart_grid']['vert_res']/2, cfg['cart_grid']['vert_res'])
    return heights


def _create_trg_grid(lons, lats, heights):
    coords = np.concatenate((lons[..., np.newaxis], lats[..., np.newaxis]), axis=-1)
    grid = np.empty((len(heights), len(lons), len(lons[0]), 3))
    grid[:, :, :, :2] = np.tile(coords, (len(heights), 1, 1, 1))
    heights_new = np.repeat(heights[:, np.newaxis, np.newaxis], len(lons), axis=1)
    heights_new = np.repeat(heights_new, len(lons[0]), axis=2)
    grid[:, :, :, 2] = heights_new
    return grid


def _check_output_exists(cfg, filetime):
    time = _get_time(filetime)
    output_file = _make_folder(cfg, time)
    if os.path.exists(output_file):
        return True
    return False


def _get_time(filetime):
    time = filetime.strip()
    time = dt.datetime.strptime(time, "%Y-%m-%d_%H%M%S")
    return time


def _make_folder(cfg, time):
    date = time.date()
    time_str = dt.datetime.strftime(time, "%H%M%S")
    if cfg['source'] == "DWD":
        output_folder = cfg['data']['RG'] + os.sep + "DWD" + os.sep
    elif cfg['source'] == "MODEL":
        output_folder = cfg['data']['RG'] + os.sep + "MODEL" + os.sep + "MP" + str(cfg['mp']) \
                        + os.sep + cfg['radar'] + os.sep
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source configuration "
                             "parameter")
    output_folder = output_folder + os.sep + str(date.year) + os.sep + f"{date.month:02d}" \
        + os.sep + f"{date.day:02d}" + os.sep
    output_folder = utils.make_folder(output_folder)
    filename = output_folder + time_str + ".nc"
    return filename


def _load_data(filename, source):
    if source == "DWD":
        handler = handles.DWDDataHandler()
        ds_data = handler.load_data(filename.strip())
    elif source == "MODEL":
        ds_data = handles.load_xarray(filename.strip())
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source configuration "
                             "parameter")
    return ds_data


def _get_src_coords(cfg, data_cart, ds_src, src, src_cart=None):
    variables = _get_variables(cfg['source'])
    if cfg['source'] == "DWD":
        src, data_cart = _get_dwd_src_coords(ds_src, variables)
    elif cfg['source'] == "MODEL":
        for var in variables:
            src_cart, data_cart[var] = _get_rf_src_coords(ds_src, cfg['sites'][cfg['radar']], var,
                                                          src_cart)
            src[var] = src_cart
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source configuration "
                             "parameter")
    return src, src_cart, data_cart


def _get_variables(source):
    if source == "DWD":
        variables = list(VARIABLES.keys())
    elif source == "MODEL":
        variables = list(VARIABLES.values())
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source configuration "
                             "parameter")
    return variables


def _get_dwd_src_coords(ds_dict, variables):
    data_dict = {}
    xyz_dict = {}
    for var, var_ds in ds_dict.items():
        if var not in variables:
            continue
        xyz, data = np.array([]).reshape((-1, 3)), np.array([])
        for _, array in var_ds.items():
            r_mesh, az_mesh = np.meshgrid(array.range.values, array.azimuth.values)
            elv = np.full(r_mesh.shape, array.elevation)
            xyz_, _ = projection.spherical_to_cart(r_mesh, az_mesh, elv, ds_dict['site_coords'])
            xyz = np.vstack((xyz, xyz_.reshape((-1, 3))))
            data = np.append(data, array.values.ravel())
        data_dict[var] = data
        xyz_dict[var] = xyz
    return xyz_dict, data_dict


def _get_rf_src_coords(ds_rf, site, var, xyz=None):
    data = np.array([])

    # If source coordinates are given, just fill the data arrays with
    # corresponding data
    if xyz is not None:
        for ele in ds_rf['elev'].values:
            array = ds_rf[var].loc[(dict(elev=ele))]
            data = np.append(data, array.values.ravel())

    # If not, calculate the Cartesian source coordinates and stack them to
    # one source coordinates array. Get the corresponding data points and
    # return it in an array of the same format.
    else:
        xyz = np.array([]).reshape((-1, 3))
        for ele in ds_rf['elev'].values:  # Do this for each elevation
            array = ds_rf.loc[(dict(elev=ele))]
            r_coord = array.range.values
            az_coord = array.azim.values
            r_mesh, az_mesh = np.meshgrid(r_coord, az_coord)  # Calculations need a mesh
            elv = np.full(r_mesh.shape, array.elev)
            xyz_, _ = projection.spherical_to_cart(r_mesh, az_mesh, elv, site)
            xyz = np.vstack((xyz, xyz_.reshape((-1, 3))))
            data = np.append(data, array[var].values.ravel())
    return xyz, data


def _data_to_grid(src, data_cart, trg_cart, itp):
    data = {}
    for var in src.keys():
        data_int, itp = projection.data_to_cart(data_cart[var], src[var], trg_cart.reshape((-1, 3)),
                                                itp=itp)
        data[var] = data_int.reshape(trg_cart.shape[:-1])
    return data, itp


def _save(ds_rg, cfg, coords, filetime):
    heights = _get_heights(cfg)
    time = _get_time(filetime)
    output = _make_folder(cfg, time)
    time_str = str(dt.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S"))
    data_dict = {}
    for var, var_data in ds_rg.items():
        if var == "DBZH":
            var = "Zhh_corr"  # DWD data is naturally attenuated
        if var == "ZDR":
            var = "Zdr_corr"
        elif cfg['source'] == "DWD":
            var = VARIABLES[var]  # Use variable names from model
        data_dict[var] = (["height", "y", "x"], var_data)
    ds_rg = xr.Dataset(data_dict, coords={'lon': (["y", "x"], coords[0]),
                                          'lat': (["y", "x"], coords[1]), 'height': heights})
    ds_rg.attrs['source'] = cfg['source']
    ds_rg.attrs['time'] = time_str
    ds_rg.attrs['vert_res'] = cfg['cart_grid']['vert_res']
    ds_rg.attrs['z_min'] = cfg['cart_grid']['z_min']
    ds_rg.attrs['z_max'] = cfg['cart_grid']['z_max']
    ds_rg.attrs['radar'] = cfg['radar']
    ds_rg.attrs['kdp_average_length'] = KDP_SMOOTH
    if cfg['mp'] is not None:
        ds_rg.attrs['MP_PHYSICS'] = cfg['mp']
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in ds_rg.variables}
    ds_rg.to_netcdf(output, encoding=encoding)


if __name__ == "__main__":
    _main(CONFIG_FILE)
