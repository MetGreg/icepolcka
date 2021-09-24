"""Save height mask

This script calculates the height of lowest and highest radar beam for each
grid box of the Regular Grid data. A mask is saved that is False for all grid
boxes that are above the highest or below the lowest radar beam.

For an explanation on how to use the configuration file, see the README file.

"""

import os
import numpy as np

from icepolcka_utils.data_base import RGDataBase
from icepolcka_utils.geo import get_target_distance, get_bin_altitude
from icepolcka_utils.utils import load_config, make_folder


def get_rg_data(path, db, update, recheck):
    """Get RegularGrid data

    Finds any RegularGrid data to get access to the grid.

    Args:
        path (str): Path to RegularGrid data.
        db (str): Path to RegularGrid data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.

    Returns:
        xarray.core.dataset.Dataset:
            Loaded RegularGrid data set.

    """
    print("Getting RG data")
    with RGDataBase(path, db, update=update, recheck=recheck) as rg_data:
        rg_handle = rg_data.get_latest_data()[0]
    data = rg_handle.load()
    return data


def get_mask(df, site, min_elv, max_elv):
    """Get distance mask

    Calculates the distance of each grid box towards the Mira-35 site and masks
    everything outside the Mira-35 range.

    Args:
        df (xarray.core.dataset.Dataset): Xarray containing the RegularGrid.
        site (list or tuple): Lon/Lat/Alt coordinates of radar site.
        min_elv (float): Minimum elevation angle of spherical radar grid.
        max_elv (float): Maximum elevation angle of spherical radar grid.

    Returns:
        numpy.ndarray:
            Height mask. True if within highest/lowest beam.

    """
    print("Getting mask")
    mask = np.empty((len(df.height), len(df.y), len(df.x)))

    for i in df.x:
        for j in df.y:
            lon = df.lon[j, i]
            lat = df.lat[j, i]
            dist = get_target_distance(site, (lon, lat))
            min_r = dist/np.arccos(np.radians(min_elv))
            max_r = dist/np.arccos(np.radians(max_elv))
            min_h = get_bin_altitude(min_r, min_elv, site_alt=site[-1])
            max_h = get_bin_altitude(max_r, max_elv, site_alt=site[-1])
            if np.isnan(max_h):  # For elevation = 90°, max_h is nan
                max_h = 15000
            mask[:, j, i] = ((df.height >= min_h) & (df.height <= max_h))
    return mask


def main():
    print("Starting main")
    cfg = load_config()
    radar = cfg['radar']
    site = cfg['sites'][radar]
    min_elv, max_elv = cfg['sphere'][radar]['elevs'][0], \
        cfg['sphere'][radar]['elevs'][-1]
    data = get_rg_data(cfg['data']['RG'], cfg['database']['RG'],
                       cfg['update'], cfg['recheck'])
    height_mask = get_mask(data, site, min_elv, max_elv)
    output = make_folder(cfg['masks']['Height']) + os.sep + radar
    np.save(output, height_mask)


if __name__ == "__main__":
    main()
