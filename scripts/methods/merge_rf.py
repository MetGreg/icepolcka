"""Merge radarfilter files

The radarfilter script is executed for each variable independently. This
script merges all files of the same time and radar to one file that includes
all variables.

Furthermore, a variable 'Zhh_corr' is added that refers to the attenuation
corrected reflectivity. Attenuation is added along the radar beam (along the
range coordinate) with the simulated attenuation.

The script only works for maximum 1 day, since a new folder is created for
each day.

The script expects the data to be located in the given data_path in
subdirectories of the following structure:
data_path/MP?/radar_name/YYYY/MM/DD/

with YYYY, MM, DD the year, month and day respectively and ? the WRF ID of
the MP scheme (which can be single or double digit).

For an explanation on how to use the configuration file, see the README file.

"""
import os
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils.utils import load_config, make_folder


def group_variables(data_path):
    """Group variables

    Group files of same timesteps together for all variables.

    Args:
        data_path (str): Path to the data files.

    Returns:
        dict:
            Dictionary with a key for each time step and a value that is list
            containing the corresponding file names.

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


def open_datasets(data_path, file_list):
    """Open datasets for all variables

    Opens the datasets for each individual variable and merge them into one
    big dataset.

    Args:
        data_path (str): Path to the data directory.
        file_list (list): List of files of the current time step containing
            the files of all variables.

    Returns:
          xarray.core.dataset.Dataset:
            Dataset that contains all variables.

    """
    ds = xr.open_dataset(data_path + file_list[0])
    for file in file_list[1:]:
        var = file[7:].split('.')[0]
        ds_var = xr.open_dataset(data_path + file)
        ds[var] = ds_var[var]
    return ds


def get_corrected_refl(ds):
    """Get corrected reflectivity

    Adds a variable 'Zhh_corr' and 'Zdr_corr' to the data set that refers to
    the reflectivity and differential reflectivity corrected by simulated
    attenuation. The correction is applied along the radar beam (along range
    coordinate).

    Args:
        ds (xarray.core.dataset.Dataset): Data set without attenuation
            corrected variable.

    Returns:
        xarray.core.dataset.Dataset:
            Data set with attenuation corrected variables 'Zhh_corr' and
            'Zdr_corr'.

    """
    res = (ds['range'][1] - ds['range'][0]).values
    ah_cum = np.nancumsum(ds['Ah'].values, axis=2)/1000*2*res
    adp_cum = np.nancumsum(ds['Adp'].values, axis=2)/1000*2*res
    zhh_corr = ds['Zhh'] - ah_cum
    zdr_corr = ds['Zdr'] - adp_cum
    ds['Zhh_corr'] = zhh_corr
    ds['Zdr_corr'] = zdr_corr
    return ds


def save(ds, time, mp, radar, output):
    """Save data to netcdf file

    Args:
        ds (xarray.core.dataset.Dataset): Dataset to be saved.
        time (datetime.datetime): Time of time step.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        output (str): Output file name.

    """
    ds['time'] = time
    ds.attrs['MP_PHYSICS'] = mp
    ds.attrs['radar'] = radar
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in ds.variables}
    ds.to_netcdf(output, encoding=encoding)


def main(cfg_file):
    cfg = load_config(cfg_file)
    assert cfg['start'].date() == cfg['end'].date(), "Only daily scripts " \
                                                     "allowed"
    date = cfg['start'].date()
    data_path = cfg['data']['RFOut'] + os.sep + "MP" + str(cfg['mp']) + os.sep \
        + cfg['radar'] + os.sep + str(date.year) + os.sep + f"{date.month:02d}"\
        + os.sep + f"{date.day:02d}" + os.sep
    file_dict = group_variables(data_path)

    print("Merging variables")
    for time_str, file_list in file_dict.items():
        time = dt.datetime.strptime(str(date) + time_str, "%Y-%m-%d%H%M%S")
        if not cfg['start'] <= time <= cfg['end']:
            continue
        print(time)
        ds = open_datasets(data_path, file_list)
        ds = get_corrected_refl(ds)
        ds = ds.drop_vars(["method", "np", "npc"])
        ds = ds.swap_dims({'naz': "azim", 'nel': "elev", 'nr': "range"})
        output_file = make_folder(cfg['data']['RF'], cfg['mp'], cfg['radar'],
                                  date)
        output_file = output_file + time_str + ".nc"
        save(ds, time, cfg['mp'], cfg['radar'], output_file)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
