"""Decrease CR-SIM file size

By removing unnecessary variables and masking outside of mira range.
Everything at heights > 15 km is put to NaN.
Data outside the Mira-35 range is put to NaN. This is done with a pre
calculated mask, the path to this mask is given via the config file.
Exceptions are the reflectivity 'Zhh' and attenuation 'Ah' as well as the
coordinates 'azim', 'elev' and 'range' because these fields are needed over the
whole domain for the radar filter and the cell tracking.

The script expects the data to be located in the given data_path in
subdirectories of the following structure:
data_path/MP?/radar_name/YYYY/MM/DD/

with YYYY, MM, DD the year, month and day respectively and ? the WRF ID of
the MP scheme (which can be single or double digit).

This script needs command line arguments:
    1) WRF ID of microphysics scheme.
    2) Radar name.
    3) Hydrometeor class name.
    4) Start time of data to be shrinked. (YYYY-mm-dd_HHMMSS)
    5) End time of data to be shrinked. (YYYY-mm-dd_HHMMSS)

The configuration file is only used to load the data_paths to CR-SIM data and
the mask. These settings should not be changed when sending jobs to the
cluster, otherwise it could happen that the configs are overwritten by
changes before the job is started on the cluster.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import sys
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils.utils import load_config, make_folder


def get_hm(data_file):
    """Get hydrometeor name

    Extracts the hydrometeor name from the file name.

    Args:
        data_file (str): File name.

    Returns:
        str:
            Name of the hydrometeor class.

    """
    hm_split = os.path.splitext(data_file)[0].split('_')
    if len(hm_split) == 1:
        hm = 'all'
    else:
        hm = hm_split[-1]
    return hm


def sanity(ds, radar):
    """Check correctness of CR-SIM output

    Sometimes, CR-SIM output had wrong attributes. This function checks if all
    output is correct. If not, the simulation should be repeated, just to be
    save.

    Args:
        ds (xarray.core.dataset.Dataset): CR-SIM dataset.
        radar (str): Radar name.

    """
    beamwidth = {'Poldirad': 1, 'Mira35': 0.6, 'Isen': 0.9}
    rad_freq = {'Poldirad': 5.5, 'Mira35': 35, 'Isen': 5.5}
    rad_res = {'Poldirad': 150, 'Mira35': 31.18, 'Isen': 250}
    indices = {'Poldirad': "161 , 127", 'Mira35': "179 , 180",
               'Isen': "192 , 273"}
    height = {'Poldirad': "603.0 m", 'Mira35': "541.0 m", 'Isen': "677.8 m"}
    scanning_mode = "elevation of each scene pixel is relative to the radar " \
        "origin"
    model_version = "crsim_v3.3"
    assert ds['rad_beamwidth'] == beamwidth[radar], "Beamwidth not correct"
    assert ds['rad_freq'] == rad_freq[radar], "Radar frequency not correct"
    assert ds['rad_range_resolution'] == rad_res[radar], "Radar resolution " \
                                                         "not correct"
    assert ds.x_and_y_indices_of_radar_position == indices[radar], "Radar " \
        "indices not correct"
    assert ds.height_of_radar == height[radar], "Radar height not correct"
    assert ds.scanning_mode == scanning_mode, "Scanning mode not correct"
    assert ds.model_version == model_version, "Model version not correct"


def drop(ds):
    """Drop unnecessary variables

    This function drops variables and attributes that are not needed.

    Args:
        ds (xarray.core.dataset.Dataset): CR-SIM dataset.

    Returns:
        xarray.core.dataset.Dataset:
            CR-SIM dataset without unnecessary variables.

    """
    ds = ds.drop_vars(["rad_freq", "rad_beamwidth", "rad_range_resolution",
                       "rad_ixc", "rad_iyc", "rad_zc", "x_scene", "y_scene"])
    if "mwr_lwp" in ds:
        ds = ds.drop_vars(["model_lwp", "mwr_lwp",
                           "number_of_gridpoints_mwrlwp"])
    if "temp" in ds:
        ds = ds.drop_vars(["temp", "rho_d", "u", "v", "w"])
    del (ds.attrs['description'], ds.attrs['model_version'],
         ds.attrs['WRF_input_file'],
         ds.attrs['x_indices_of_WRF_extracted_scene'],
         ds.attrs['y_indices_of_WRF_extracted_scene'],
         ds.attrs['z_indices_of_WRF_extracted_scene'],
         ds.attrs['scene_extracted_at_time_step'],
         ds.attrs['x_and_y_indices_of_radar_position'],
         ds.attrs['height_of_radar'], ds.attrs['scanning_mode'],
         ds.attrs['created_by'], ds.attrs['institute'], ds.attrs['websites'],
         ds.attrs['radar_frequency'])
    return ds


def mask_ds(ds, mask, z_max):
    """Mask Mira-35 range

    Puts all variables outside of Mira-35-range to NaN. Exceptions are: 'Zhh',
    'Ah', 'elev', 'azim', 'range'. These variables are needed over the whole
    domain for the radar filter and cell tracking.


    Args:
        ds (xarray.core.dataset.Dataset): CR-SIM dataset.
        mask (numpy.ndarray): Loaded distance mask.
        z_max (int): Maximum height [m].

    Returns:
        xarray.core.dataset.Dataset:
            CR-SIM dataset where heights above zmax have been masked.

    """
    variables = ["Zvv", "Zvh", "Zdr", "LDRh", "RHOhv", "DV", "SWh", "SWt",
                 "SWs", "SWv", "SWtot", "DV90", "SWh90", "RWV", "Kdp", "Adp",
                 "Av", "diff_back_phase", "wcont"]
    for var in variables:
        ds[var].values = np.where(~mask, ds[var].values, np.nan)
        ds[var].values = np.where(ds['height'].values < z_max, ds[var].values,
                                  np.nan)
    if "Zmin" in ds:
        ds['Zmin'].values = np.where(~mask, ds['Zmin'].values, np.nan)
        ds['Zmin'].values = np.where(ds['height'].values < z_max,
                                     ds['Zmin'].values, np.nan)
    ds['Zhh'].values = np.where(ds['height'].values < z_max, ds['Zhh'].values,
                                np.nan)
    ds['height'].values = np.where(ds['height'].values < z_max,
                                   ds['height'].values, np.nan)
    return ds


def save(ds, time, mp, radar, hm, output):
    """Save data to netcdf file

    Args:
        ds (xarray.core.dataset.Dataset): Dataset to be saved.
        time (datetime.datetime): Time of time step [UTC].
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        hm (str): Name of hydrometeor class.
        output (str): Output file name.

    """
    ds = ds.set_coords(["xlong", "xlat"])
    ds = ds.rename({'xlong': "lon", 'xlat': "lat"})
    ds['time'] = time
    ds.attrs['radar'] = radar
    ds.attrs['MP_PHYSICS'] = mp
    ds.attrs['hydrometeor'] = hm
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in ds.variables}
    ds.to_netcdf(output, encoding=encoding)


def main(start, end, mp, radar, hm, cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    start = dt.datetime.strptime(start, "%Y-%m-%d_%H%M%S")
    end = dt.datetime.strptime(end, "%Y-%m-%d_%H%M%S")
    mask = np.load(cfg['masks']['Distance'])
    assert start.date() == end.date(), "Only daily scripts allowed"
    date = start.date()

    data_path = cfg['data']['CRSIMOut'] + os.sep + "MP" + str(mp) + os.sep \
        + radar + os.sep + str(date.year) + os.sep + f"{date.month:02d}" \
        + os.sep + f"{date.day:02d}" + os.sep

    print("Running shrink for each data file")
    for data_file in sorted(os.listdir(data_path)):
        file_hm = get_hm(data_file)
        time_str = data_file[:6]
        time = dt.datetime.strptime(str(date) + time_str, "%Y-%m-%d%H%M%S")
        if not start <= time <= end:
            continue
        if hm != file_hm:
            continue
        print(data_file)
        ds = xr.open_dataset(data_path + data_file)
        sanity(ds, radar)
        ds = drop(ds)
        ds = mask_ds(ds, mask, cfg['cart_grid']['z_max'])
        output_file = make_folder(cfg['data']['CRSIM'], mp, radar, date, hm=hm)
        output_file = output_file + time_str + ".nc"
        save(ds, time, mp, radar, hm, output_file)


if __name__ == "__main__":
    start_time = sys.argv[1]
    end_time = sys.argv[2]
    mp_id = sys.argv[3]
    radar_name = sys.argv[4]
    hm_name = sys.argv[5]
    config_file = sys.argv[6]
    main(start_time, end_time, mp_id, radar_name, hm_name, config_file)
