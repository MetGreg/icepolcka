"""Applies the rf mask on the rg data

Some variables are available on the whole domain. All my analysis happens on the smaller
Mira-subdomain. To save disk space, this function applies a mask to these radar fields that puts
all values outside the Mira-range to NaN.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg data path
    database: RG
      - The rg database file path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be processed
    source
      - The input data source ('MODEL' or 'DWD')
    update
      - Whether to update the CR-SIM database with new files
    masks: RF
      - The output path of the rf mask

"""
import datetime as dt

import numpy as np

from icepolcka_utils import utils
from icepolcka_utils.database import interpolations, main

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
CRSIM_VARIABLES = ["Zdr", "Zdr_corr", "LDRh", "RHOhv", "Kdp", "Ah", "Adp"]
DWD_VARIABLES = ["Zdr_corr", "RHOhv", "Kdp"]


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    mask = np.load(cfg['masks']['RF']).astype(bool)
    handles = main.get_handles(interpolations.RGDataBase, cfg, "RG", mp_id=cfg['mp'],
                               source=cfg['source'], radar=cfg['radar'])
    variables = CRSIM_VARIABLES
    if cfg['source'] == "DWD":
        variables = DWD_VARIABLES

    for handle in handles:
        print(handle['file_path'])
        data = handle.load()
        data_new = data.load()
        data.close()
        for var in variables:
            data_new[var].values = np.where(~mask, data_new[var].values, np.nan)
        time_str = str(dt.datetime.strptime(str(data_new.time), "%Y-%m-%d %H:%M:%S"))
        data_new.attrs['time'] = time_str
        if cfg['source'] == "DWD":
            del data_new.attrs['mp']
        data_new.to_netcdf(handle['file_path'])


if __name__ == "__main__":
    _main(CONFIG_FILE)
