"""Decrease CR-SIM file size

By removing unnecessary variables and masking outside Mira-35 range. Everything at heights > 15 km
is put to NaN. Data outside the Mira-35 range is put to NaN for most variables (except the ones that
are needed later on for the radar filter and cell tracking). This is done with a precalculated mask
(from the script save_distance_mask.py), the path to this mask is given via the config file.

The script expects the data to be located in the given data_path in subdirectories of the following
structure:
data_path/MP?/radar_name/YYYY/MM/DD/

with YYYY, MM, DD the year, month and day respectively and ? the WRF ID of the MP scheme (which can
be single or double-digit).

This script needs command line arguments:
    1) WRF ID of microphysics scheme.
    2) Radar name.
    3) Hydrometeor class name.
    4) Start time of data to be shrinked. (YYYY-mm-dd_HHMMSS)
    5) End time of data to be shrinked. (YYYY-mm-dd_HHMMSS)

The configuration file is only used to load the data_paths to CR-SIM data and the mask. These
settings should not be changed when sending jobs to the cluster, otherwise it could happen that the
configs are overwritten by changes before the job is started on the cluster.

"""
import os
import sys
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils import utils

CONFIG_FILE = "job_config.yaml"


def _get_hm(data_file):
    """Get hydrometeor name

    Extracts the hydrometeor name from the file name.

    Args:
        data_file (str): File name.

    Returns:
        str:
            Name of the hydrometeor class.

    """
    hm_split = os.path.splitext(data_file)[0].split("_")
    if len(hm_split) == 1:
        hm_name = "all"
    else:
        hm_name = hm_split[-1]
    return hm_name


def _sanity(data, radar):
    """Check correctness of CR-SIM output

    Sometimes, CR-SIM output had wrong attributes. This function checks if all output is correct.
    If not, the simulation should be repeated, just to be save.

    Args:
        data (xarray.core.dataset.Dataset): CR-SIM dataset.
        radar (str): Radar name.

    """
    beamwidth = {'Poldirad': 1, 'Mira35': 0.6, 'Isen': 0.9}
    rad_freq = {'Poldirad': 5.5, 'Mira35': 35, 'Isen': 5.5}
    rad_res = {'Poldirad': 150, 'Mira35': 31.18, 'Isen': 250}
    indices = {'Poldirad': "161 , 127", 'Mira35': "179 , 180", 'Isen': "192 , 273"}
    height = {'Poldirad': "603.0 m", 'Mira35': "541.0 m", 'Isen': "677.8 m"}
    scanning_mode = "elevation of each scene pixel is relative to the radar origin"
    model_version = "crsim_v3.3"
    assert data['rad_beamwidth'] == beamwidth[radar], "Beamwidth not correct"
    assert data['rad_freq'] == rad_freq[radar], "Radar frequency not correct"
    assert data['rad_range_resolution'] == rad_res[radar], "Radar resolution not correct"
    assert data.x_and_y_indices_of_radar_position == indices[radar], "Radar indices not correct"
    assert data.height_of_radar == height[radar], "Radar height not correct"
    assert data.scanning_mode == scanning_mode, "Scanning mode not correct"
    assert data.model_version == model_version, "Model version not correct"


def _drop(data):
    """Drop unnecessary variables

    This function drops variables and attributes that are not needed.

    Args:
        data (xarray.core.dataset.Dataset): CR-SIM dataset.

    Returns:
        xarray.core.dataset.Dataset:
            CR-SIM dataset without unnecessary variables.

    """
    if "mwr_lwp" in data:
        data = data.drop_vars(["model_lwp", "mwr_lwp", "number_of_gridpoints_mwrlwp"])
    if "temp" in data:
        data = data.drop_vars(["temp", "rho_d", "u", "v", "w"])
    del (data.attrs['description'], data.attrs['model_version'],
         data.attrs['WRF_input_file'],
         data.attrs['x_indices_of_WRF_extracted_scene'],
         data.attrs['y_indices_of_WRF_extracted_scene'],
         data.attrs['z_indices_of_WRF_extracted_scene'],
         data.attrs['scene_extracted_at_time_step'],
         data.attrs['x_and_y_indices_of_radar_position'],
         data.attrs['height_of_radar'], data.attrs['scanning_mode'],
         data.attrs['created_by'], data.attrs['institute'], data.attrs['websites'],
         data.attrs['radar_frequency'])
    return data


def _mask_data(data, mask, z_max):
    """Mask Mira-35 range

    Puts most variables outside Mira-35-range to NaN.

    Args:
        data (xarray.core.dataset.Dataset): CR-SIM dataset.
        mask (numpy.ndarray): Loaded distance mask.
        z_max (int): Maximum height [m].

    Returns:
        xarray.core.dataset.Dataset:
            CR-SIM dataset where heights above zmax have been masked.

    """
    variables = ["Zvv", "Zvh", "Zdr", "LDRh", "RHOhv", "DV", "SWh", "SWt", "SWs", "SWv", "SWtot",
                 "DV90", "SWh90", "RWV", "Kdp", "Av", "diff_back_phase", "wcont"]
    for var in variables:
        data[var].values = np.where(~mask, data[var].values, np.nan)
        data[var].values = np.where(data['height'].values < z_max, data[var].values, np.nan)
    if "Zmin" in data:
        data['Zmin'].values = np.where(~mask, data['Zmin'].values, np.nan)
        data['Zmin'].values = np.where(data['height'].values < z_max, data['Zmin'].values, np.nan)
    data['Zhh'].values = np.where(data['height'].values < z_max, data['Zhh'].values, np.nan)

    # Add all variables to the new data set and cut all heights >= 30
    data = data.set_coords(["xlong", "xlat"])
    data = data.rename({'xlong': "lon", 'xlat': "lat"})
    ds_new = xr.Dataset(coords={'lon': data['lon'], 'lat': data['lat']})
    for k in data.variables:
        if "nz" in data[k].dims:  # Cut only variables that have a height
            ds_new[k] = data[k].where(data[k].nz < 29, drop=True)
        else:
            ds_new[k] = data[k]

    # Add attributes
    for attr in data.attrs:
        ds_new.attrs[attr] = data.attrs[attr]
    ds_new.load()  # Load the new data set before closing the old one
    data.close()
    return ds_new


def _save(data, cfg, time, hm_name, output):
    """Save data to netcdf file

    Saves the data set after transposing the dimensions. This is necessary for applying the radar
    filter in the following method step which needs a very specific order of the dimensions.

    Args:
        data (xarray.core.dataset.Dataset): Dataset to be saved.
        cfg (dict): Configuration dictionary.
        time (datetime.datetime): Time of time step [UTC].
        hm_name (str): Name of hydrometeor class.
        output (str): Output file name.

    """
    data = data.transpose("one", "nz", "nx", "ny")
    data.attrs['radar'] = cfg['radar']
    data.attrs['MP_PHYSICS'] = cfg['mp']
    data.attrs['hydrometeor'] = hm_name
    data['time'] = time
    encoding = {k: {'zlib': True, 'fletcher32': True, '_FillValue': -9999} for k in data.variables}
    data.to_netcdf(output, encoding=encoding)


def _main(cfg_file, hm_name):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    mask = np.load(cfg['masks']['Distance'])
    assert cfg['start'].date() == cfg['end'].date(), "Time cannot exceed 1 day"
    date = cfg['start'].date()

    data_path = cfg['data']['CRSIMOut'] + os.sep + "MP" + str(cfg['mp']) + os.sep + cfg['radar'] \
        + os.sep + str(date.year) + os.sep + f"{date.month:02d}" + os.sep + f"{date.day:02d}" \
        + os.sep

    print("Running shrink for each data file")
    for data_file in sorted(os.listdir(data_path)):
        file_hm = _get_hm(data_file)
        time_str = data_file[:6]
        time = dt.datetime.strptime(str(date) + time_str, "%Y-%m-%d%H%M%S")
        if not cfg['start'] <= time <= cfg['end']:
            continue
        if hm_name != file_hm:
            continue
        print(data_file)
        data = xr.open_dataset(data_path + data_file)
        _sanity(data, cfg['radar'])
        data = _drop(data)
        data = _mask_data(data, mask, cfg['cart_grid']['z_max'])
        output_file = utils.make_folder(cfg['data']['CRSIM'], cfg['mp'], cfg['radar'], date,
                                        hm_name=hm_name)
        output_file = output_file + time_str + ".nc"
        _save(data, cfg, time, hm_name, output_file)


if __name__ == "__main__":
    hm_input = sys.argv[1]
    _main(CONFIG_FILE, hm_input)
