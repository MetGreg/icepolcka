"""Readding radar resolution to CRSIM-output

For disk space reasons, the original CRSIM-output was shrinked using the
script shrink_data.py. The radar filter script needs information that was
deleted from the files. This script readds this information. This concerns
radar resolutions, radar beamwidths, radar heights and the index (x, y) of the
radar in the wrf grid.

Furthermore, the radar filter cannot work with 'NaN' values in the height
coordinate. The shrink_data script put all heights above 15 km to NaN. To
work with the radar filter, this script removes all values at height step
30 (which roughly corresponds to height 15 km) and above so that there is no
NaN value left in the data.

For an explanation on how to use the configuration file, see the README file.

"""
import numpy as np
import xarray as xr

from icepolcka_utils.data_base import CRSIMDataBase
from icepolcka_utils.utils import load_config


# Settings that are not defined by the configuration file
RAD_RES = {'Isen': 250, 'Poldirad': 150, 'Mira35': 31.1792}
RAD_BW = {'Isen': 0.9, 'Poldirad': 1.0, 'Mira35': 0.6}
RAD_IDX = {'Isen': (192, 273), 'Poldirad': (161, 127), 'Mira35': (179, 180)}
RAD_HGT = {'Isen': 678, 'Poldirad': 603, 'Mira35': 541}


def get_crsim_data(path, db, update, recheck, start, end, mp, radar):
    """Get CR-SIM data

    Finds any CR-SIM data to get access to the grid. The CR-SIM and WRF grid
    are the same.

    Args:
        path (str): Path to CR-SIM data.
        db (str): Path to CR-SIM data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.

    Returns:
        list:
            List containing ResultHandles of corresponding data within
                configured time range.

    """
    print("Getting CR-SIM data")
    with CRSIMDataBase(path, db, update=update, recheck=recheck) as data_base:
        handles = data_base.get_data(start, end, mp_id=mp, radar=radar)
    return handles


def get_data_arrays(radar):
    """Get data arrays

    Prepare xarray DataArrays that contain the missing information to be
    added to the CR-SIM data set. This concerns radar range resolution,
    beamwidth, radar site index (x, y) and the grid x and y coordinates.

    Args:
        radar (str): Radar name.

    Returns:
        tuple:
            1) Xarray DataArray of radar range resolution.
            2) Xarray DataArray of radar beamwidth.
            3) Xarray DataArray of radar site x index.
            4) Xarray DataArray of radar site y index.
            5) Xarray DataArray of radar site height [m].
            6) Xarray DataArray of radar grid x coordinates.
            7) Xarray DataArray of radar grid y coordinates.

    """
    print("Getting data arrays")
    res = RAD_RES[radar]
    bw = RAD_BW[radar]
    ix = RAD_IDX[radar][0]
    iy = RAD_IDX[radar][1]
    z = RAD_HGT[radar]
    da_rr = xr.DataArray([res], dims=['one'])
    da_bw = xr.DataArray([bw], dims=['one'])
    da_ix = xr.DataArray([ix], dims=['one'])
    da_iy = xr.DataArray([iy], dims=['one'])
    da_z = xr.DataArray([z], dims=['one'])
    da_x_scene = xr.DataArray(np.arange(0, 143601, 400), dims=['nx'])
    da_y_scene = xr.DataArray(np.arange(0, 143601, 400), dims=['ny'])
    return da_rr, da_bw, da_ix, da_iy, da_z, da_x_scene, da_y_scene


def add_missing_info(handle, da_rr, da_bw, da_ix, da_iy, da_z, da_x_scene,
                     da_y_scene):
    """Add missing information

    Readds all information to the CR-SIM dataset that is missing. This concerns
    radar range resolution, beamwidth, radar site coordinates (x, y) and the
    grid x and y coordinates.

    Also drops all heights at height step >= 30, as CR-SIM cannot work with
    NaN and they have been put to NaN by the shrink script before.

    Args:
        handle (ResultHandle): ResultHandle containing the CR-SIM data.
        da_rr (xarray.core.dataset.Dataset): DataArray containing the radar
            range resolution.
        da_bw (xarray.core.dataset.Dataset): DataArray containing the radar
            beamwidth.
        da_ix (xarray.core.dataset.Dataset): DataArray containing the radar site
            x index.
        da_iy (xarray.core.dataset.Dataset): DataArray containing the radar site
            y index.
        da_z (xarray.core.dataset.Dataset): DataArray containing the radar site
            height [m].
        da_x_scene (xarray.core.dataset.Dataset): DataArray containing the radar
            grid x coordinates.
        da_y_scene (xarray.core.dataset.Dataset): DataArray containing radar the
            radar grid y coordinates.

    Returns:
        xarray.core.dataset.Dataset:
            Dataset where missing information has been readded.

    """
    ds = handle.load()
    ds_new = xr.Dataset(coords={'lon': ds['lon'], 'lat': ds['lat']})

    # Add all variables to the new data set and cut all heights >= 30
    for k in ds.variables:
        if "nz" in ds[k].dims:  # Cut only variables that have a height
            ds_new[k] = ds[k].where(ds[k].nz < 29, drop=True)
        else:
            ds_new[k] = ds[k]

    # Add attributes
    for attr in ds.attrs:
        ds_new.attrs[attr] = ds.attrs[attr]
    ds_new.load()  # Load the new data set before closing the old one
    ds.close()

    # Readd missing information
    ds_new['rad_range_resolution'] = da_rr
    ds_new['rad_beamwidth'] = da_bw
    ds_new['rad_ixc'] = da_ix
    ds_new['rad_iyc'] = da_iy
    ds_new['rad_zc'] = da_z
    ds_new['x_scene'] = da_x_scene
    ds_new['y_scene'] = da_y_scene

    del ds_new.attrs['time']  # Time attribute not needed
    return ds_new


def save(ds, filename):
    """Save data set

    Saves the data set after transposing the dimensions. This is necessary
    for applying the radar filter in the following method step which needs a
    very specific order of the dimensions.

    Args:
        ds (xarray.core.dataset.Dataset): CR-SIM dataset with readded
            information.
        filename (str): Path to the output file.

    """
    ds = ds.transpose("one", "nz", "nx", "ny")
    # Encoding with zlib and fletcher32 to decrease disk space
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in
                ds.variables}
    ds.to_netcdf(filename, encoding=encoding)


def main():
    print("Starting Main")
    cfg = load_config()
    handles = get_crsim_data(cfg['data']['CRSIM'], cfg['database']['CRSIM'],
                             cfg['update'], cfg['recheck'], cfg['start'],
                             cfg['end'], cfg['mp'], cfg['radar'])
    da_rr, da_bw, da_ix, da_iy, da_z, da_x_scene, da_y_scene = \
        get_data_arrays(cfg['radar'])

    print("Readding information")
    for handle in handles:
        filename = handle['file_path']
        print(filename)
        ds = add_missing_info(handle, da_rr, da_bw, da_ix, da_iy, da_z,
                              da_x_scene, da_y_scene)
        save(ds, filename)


if __name__ == "__main__":
    main()
