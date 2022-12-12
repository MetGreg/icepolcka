"""Saves a mask for ranges outside Mira-35 range after RF-transformation

The radar filter script changes the grid slightly. This script creates a mask for grid boxes outside
the Mira-35 range after the RF transformation and interpolation back to a radar grid. This mask is
True, if the grid box is outside the Mira-35 range.

It works by loading an RG-file and look at the ZDR-field, which was masked exactly to the Mira-35
range before the RF-transformation. This script simply saves the resulting NaN-field.

The RG-file that is loaded is defined in the beginning as a global variable 'RG_FILE' and must be
adjusted.

The nan field is taken from height step 16 (which equals to 1.5 km --> Most of my analysis
happens at this height).

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    masks: RF
      - The output path of the rf mask

"""
import os
import numpy as np

from icepolcka_utils import utils
from icepolcka_utils.database import handles

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
RG_FILE = "/project/meteo/work/Gregor.Koecher/icepolcka/data/rg/MODEL/MP8/Isen/2019/05/28/120000.nc"


def _main():
    cfg = utils.get_cfg(CONFIG_FILE)
    data = handles.load_xarray(RG_FILE)
    mask = np.isnan(data['Zdr'].values[16])
    mask_folder_split = cfg['masks']['RF'].split(os.sep)[:-1]
    mask_folder = os.sep.join(mask_folder_split)
    utils.make_folder(mask_folder)
    np.save(cfg['masks']['RF'], mask)


if __name__ == "__main__":
    _main()
