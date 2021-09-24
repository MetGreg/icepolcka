"""Saves a mask for ranges outside of Mira-35 range

The mask refers to the WRF grid. For each of the surface grid boxes,
the distance to the Mira-35 site is calculated. A mask for all grid boxes
outside the Mira-35 range is saved. This mask is True, if the grid box is
outside of the Mira-35 range.

For an explanation on how to use the configuration file, see the README file.

"""
import numpy as np

from icepolcka_utils.data_base import WRFDataBase
from icepolcka_utils.geo import get_target_distance
from icepolcka_utils.utils import load_config, make_folder


def get_wrf_data(path, db, update, recheck):
    """Get WRF data

    Finds any WRF data to get access to the grid.

    Args:
        path (str): Path to WRF data.
        db (str): Path to WRF data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.

    Returns:
        xarray.core.dataset.Dataset:
            Loaded WRF data set.

    """
    print("Getting WRF data")
    with WRFDataBase(path, db, update=update, recheck=recheck) as wrf_data:
        wrf_handle = wrf_data.get_latest_data()[0]
    data = wrf_handle['clouds'].load()
    return data


def get_coords(data):
    """Get grid coordinates

    Gets the lon/lat grid coordinates of the WRF grid.

    Args:
        data (xarray.core.dataset.Dataset): Dataset that contains the WRF
            grid.

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


def get_mask(mira_coords, coords, r_max, grid_shape):
    """Get distance mask

    Calculates the distance of each grid box towards the Mira-35 site and masks
    everything outside the Mira-35 range.

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
    dist = np.array([get_target_distance(mira_coords[:2], c) for c in coords])
    dist = dist.reshape(grid_shape)
    mask = np.full(dist.shape, False)
    idx = np.where(dist > r_max)
    mask[idx] = True
    return mask


def main():
    print("Starting main")
    cfg = load_config()
    data = get_wrf_data(cfg['data']['WRF'], cfg['database']['WRF'],
                        cfg['update'], cfg['recheck'])
    mira_coords = cfg['sites']['Mira35']
    wrf_coords, grid_shape = get_coords(data)
    crsim_mask = get_mask(mira_coords, wrf_coords, cfg['max_r'], grid_shape)
    make_folder(cfg['masks']['Distance'])
    np.save(cfg['masks']['Distance'], crsim_mask)


if __name__ == "__main__":
    main()
