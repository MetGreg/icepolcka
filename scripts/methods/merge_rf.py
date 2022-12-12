"""Merge radarfilter files

The radarfilter script is executed for each variable independently. This script merges all files of
the same time and radar to one file that includes all variables.

Furthermore, a variable 'Zhh_corr' is added that refers to the attenuation corrected reflectivity.
Attenuation is added along the radar beam (along the range coordinate) with the simulated
attenuation.

The script only works for maximum 1 day, since a new folder is created for each day.

The script expects the data to be located in the given data_path in subdirectories of the following
structure:
data_path/MP?/radar_name/YYYY/MM/DD/

with YYYY, MM, DD the year, month and day respectively and ? the WRF ID of the MP scheme (which can
be single or double-digit).

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RFOut
      - Unprocessed rf output data path
    data: RF
      - Output for merged rf data
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be simulated

"""
import os
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils import utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _group_variables(data_path):
    """Group variables

    Group files of same timesteps together for all variables.

    Args:
        data_path (str): Path to the data files.

    Returns:
        dict:
            Dictionary with a key for each time step and a value that is list containing the
            corresponding file names.

    """
    print("Grouping variables")
    file_dict = {}
    for data_file in sorted(os.listdir(data_path)):
        time_str = data_file[:6]
        if time_str not in file_dict.keys():
            file_dict[time_str] = [data_file]
        else:
            file_dict[time_str].append(data_file)
    return file_dict


def _open_datasets(data_path, file_list):
    """Open datasets for all variables

    Opens the datasets for each individual variable and merge them into one big dataset.

    Args:
        data_path (str): Path to the data directory.
        file_list (list): List of files of the current time step containing the files of all
            variables.

    Returns:
          xarray.core.dataset.Dataset:
            Dataset that contains all variables.

    """
    data = xr.open_dataset(data_path + file_list[0])
    for file in file_list[1:]:
        var = file[7:].split('.')[0]
        ds_var = xr.open_dataset(data_path + file)
        data[var] = ds_var[var]
    return data


def _get_corrected_refl(data):
    """Get corrected reflectivity

    Adds a variable 'Zhh_corr' and 'Zdr_corr' to the data set that refers to the reflectivity and
    differential reflectivity corrected by simulated attenuation. The correction is applied along
    the radar beam (along range coordinate).

    Args:
        data (xarray.core.dataset.Dataset): Data set without attenuation corrected variable.

    Returns:
        xarray.core.dataset.Dataset:
            Data set with attenuation corrected variables 'Zhh_corr' and 'Zdr_corr'.

    """
    res = (data['range'][1] - data['range'][0]).values
    ah_cum = np.nancumsum(data['Ah'].values, axis=2)/1000*2*res
    adp_cum = np.nancumsum(data['Adp'].values, axis=2)/1000*2*res
    zhh_corr = data['Zhh'] - ah_cum
    zdr_corr = data['Zdr'] - adp_cum
    data['Zhh_corr'] = zhh_corr
    data['Zdr_corr'] = zdr_corr
    return data


def _save(data, time, mp_id, radar, output):
    """Save data to netcdf file

    Args:
        data (xarray.core.dataset.Dataset): Dataset to be saved.
        time (datetime.datetime): Time of time step.
        mp_id (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        output (str): Output file name.

    """
    data['time'] = time
    data.attrs['MP_PHYSICS'] = mp_id
    data.attrs['radar'] = radar
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in data.variables}
    data.to_netcdf(output, encoding=encoding)


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    assert cfg['start'].date() == cfg['end'].date(), "Time cannot exceed 1 day"
    date = cfg['start'].date()
    data_path = cfg['data']['RFOut'] + os.sep + "MP" + str(cfg['mp']) + os.sep \
        + cfg['radar'] + os.sep + str(date.year) + os.sep + f"{date.month:02d}"\
        + os.sep + f"{date.day:02d}" + os.sep
    file_dict = _group_variables(data_path)

    print("Merging variables")
    for time_str, file_list in file_dict.items():
        time = dt.datetime.strptime(str(date) + time_str, "%Y-%m-%d%H%M%S")
        if not cfg['start'] <= time <= cfg['end']:
            continue
        print(time)
        data = _open_datasets(data_path, file_list)
        data = _get_corrected_refl(data)
        data = data.drop_vars(["method", "np", "npc"])
        data = data.swap_dims({'naz': "azim", 'nel': "elev", 'nr': "range"})
        output_file = utils.make_folder(cfg['data']['RF'], cfg['mp'], cfg['radar'], date)
        output_file = output_file + time_str + ".nc"
        _save(data, time, cfg['mp'], cfg['radar'], output_file)


if __name__ == "__main__":
    _main(CONFIG_FILE)
