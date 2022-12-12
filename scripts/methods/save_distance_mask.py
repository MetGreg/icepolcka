"""Saves a mask for ranges outside Mira-35 range

The mask refers to the WRF grid. For each of the surface grid boxes, the distance to the Mira-35
site is calculated. A mask for all grid boxes outside the Mira-35 range is saved. This mask is True,
if the grid box is outside the Mira-35 range.

The WRF-file that is loaded to access the grid is defined in the beginning as a global variable
'WRF_FILE' and must be adjusted.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    masks: Distance
      - Output path of the mask
    sites: Mira35
      - Mira radar location (lon, lat, alt)
    r_max
      - Maximum allowed distance to center (m)

"""
import os
import numpy as np

from icepolcka_utils.database import handles
from icepolcka_utils import geo, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
WRF_FILE = "/project/meteo/work/Gregor.Koecher/icepolcka/data/wrf/icepolcka/2019/05/28/MP8" \
           "/clouds_d03_2019-05-28_120000"


def _get_coords(data):
    """Get grid coordinates

    Gets the lon/lat grid coordinates of the WRF grid.

    Args:
        data (xarray.core.dataset.Dataset): Dataset that contains the WRF grid.

    Returns:
        (numpy.ndarray, tuple):
            1) Array of lon/lat coordinates of each grid point.
            2) Tuple of the grid shape.

    """
    print("Getting coordinates")
    grid_shape = data['XLONG'][0].shape
    lons = data['XLONG'][0].values.ravel()
    lats = data['XLAT'][0].values.ravel()
    coords = np.concatenate((lons[:, np.newaxis], lats[:, np.newaxis]), axis=-1)
    return coords, grid_shape


def _get_mask(mira_coords, coords, r_max, grid_shape):
    """Get distance mask

    Calculates the distance of each grid box towards the Mira-35 site and masks everything outside
    the Mira-35 range.

    Args:
        mira_coords (list or tuple): lon/lat/alt coordinates of Mira-35 site.
        coords (numpy.ndarray): Array of lon/lat coordinates of each grid point.
        r_max (int): Maximum grid height.
        grid_shape (tuple): Grid shape.

    Returns:
        numpy.ndarray:
            Distance mask. True if outside Mira-35 range.

    """
    print("Getting mask")
    dist = np.array([geo.get_target_distance(mira_coords[:2], c) for c in coords])
    dist = dist.reshape(grid_shape)
    mask = np.full(dist.shape, False)
    idx = np.where(dist > r_max)
    mask[idx] = True
    return mask


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    data = handles.load_wrf_data(WRF_FILE)
    mira_coords = cfg['sites']['Mira35']
    wrf_coords, grid_shape = _get_coords(data)
    crsim_mask = _get_mask(mira_coords, wrf_coords, cfg['max_r'], grid_shape)
    mask_folder_split = cfg['masks']['Distance'].split(os.sep)[:-1]
    mask_folder = os.sep.join(mask_folder_split)
    utils.make_folder(mask_folder)
    np.save(cfg['masks']['Distance'], crsim_mask)


if __name__ == "__main__":
    _main(CONFIG_FILE)
