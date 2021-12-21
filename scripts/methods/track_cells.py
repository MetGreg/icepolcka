"""Track cells

This script tracks convective cells for DWD as well as MODEL data. Most code
is based on TINT. The script finds RegularGrid data according to
configuration, creates a PyArtGrid from each RegularGrid and passes these
PyArtGrids to the TINT cell tracking. The tracks are then saved to pkl files.

The TINT cell tracking needs some parameters. These are defined at the top of
the script. These settings are the default TINT settings.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import pickle
import datetime as dt
import numpy as np
import xarray as xr

from icepolcka_utils.data_base import RGDataBase
from icepolcka_utils.grid import get_pyart_grids
from icepolcka_utils.tracks import CellTracks
from icepolcka_utils.utils import load_config, make_folder


def get_data_base(cfg):
    """Get data base

    Some settings (microphysics, radar name) depend on the source of the
    data (DWD or MODEL). This function returns the corresponding settings. The
    input configuration dictionary must contain all keywords necessary.

    For an explanation on how to use the configuration file, see the README
    file.

    Args:
        cfg (dict): Configuration dictionary.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        (int, str)
            1) WRF ID of microphysics scheme.
            2) Radar name.

    """
    print("Getting data base")
    if cfg['source'] == "DWD":
        mp = None
        radar = "Isen"
    elif cfg['source'] == "MODEL":
        mp = cfg['mp']
        radar = cfg['radar']
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")

    return mp, radar


def get_handles(grid_path, grid_db, update, recheck, start, end, source, mp,
                radar):
    """Get data handles

    Gets the handles from the data base corresponding to the data within the
    time range, radar, microphysics and data source that was configured. The
    length of the handles must always be equal to 288, which is exactly one
    day of 5-min timesteps, because this script is supposed to be run on
    exactly one day.

    Args:
        grid_path (str): Path to data.
        grid_db (str): Path to data base file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        source (str): Whether to find 'DWD' or 'MODEL' data.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Name of the radar.

    Raises:
        AssertionError: When the length of the handles does not equal 288.

    Returns:
        list:
            List of all data handles corresponding to configured input.

    """
    print("Getting handles")
    with RGDataBase(grid_path, grid_db, update=update, recheck=recheck) as \
            grid_data:
        handles = grid_data.get_data(start, end, source=source, mp_id=mp,
                                     radar=radar)
    print("Found: ", len(handles))
    assert len(handles) == 288, "Grid handles have wrong length. MP: " \
                                + str(mp) + "Date: " + str(start.date())
    sorted_handles = sorted(handles, key=lambda k: k['time'])
    return sorted_handles


def track_cells(grids, track_params):
    """Track convective cells

    This function revokes the actual cell tracking. A CellTracks object is
    created with given configurations and the cell tracking is applied for
    the input PyArtGrid.

    Args:
        grids (list): List of PyArtGrids.
        track_params (dict): Containing TINT tracking configuration.

    Returns:
        CellTracks:
            CellTracks object that contains all cell tracks.

    """
    print("Tracking cells")
    # Get cell tracks
    tracks_obj = CellTracks(params=track_params)
    tracks_obj.get_tracks(iter(grids))
    return tracks_obj


def save(tracks, date, source, mp, radar, output):
    """Save data to netcdf file

    Args:
        tracks (pandas.core.frame.DataFrame): Tracks to be saved.
        date (str): Date of the tracks.
        source (str): Whether the tracks come from 'DWD' or 'MODEL' data.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        output (str): Output file name.

    """
    print("Saving data")
    ds = xr.Dataset.from_dataframe(tracks)
    ds.attrs['date'] = date
    ds.attrs['source'] = source
    if mp is not None:
        ds.attrs['MP_PHYSICS'] = mp
    if radar is not None:
        ds.attrs['radar'] = radar

    with open(output, "wb") as f:
        dumps = pickle.dumps(ds, protocol=-1)
        pickle.dump(dumps, f, protocol=4)
    ds.close()


def main(cfg_file):
    cfg = load_config(cfg_file)
    mp, radar = get_data_base(cfg)
    mask = np.load(cfg['masks']['Height'] + os.sep + radar + ".npy")
    start = dt.datetime(cfg['date'].year, cfg['date'].month, cfg['date'].day, 0,
                        0, 0)
    end = dt.datetime(cfg['date'].year, cfg['date'].month, cfg['date'].day,
                      23, 59, 59)
    handles = get_handles(cfg['data']['RG'], cfg['database']['RG'],
                          cfg['update'], cfg['recheck'], start, end,
                          cfg['source'], mp, radar)
    grids = get_pyart_grids(handles, mask)
    tracks = track_cells(grids, cfg['tracking'])
    output = cfg['data']['TRACKS'] + os.sep + cfg['source'] + os.sep
    output_folder = make_folder(output, mp, radar)
    date_str = dt.datetime.strftime(cfg['date'], "%Y-%m-%d")
    filename = output_folder + date_str + ".pkl"
    save(tracks.tracks, date_str, cfg['source'], mp, radar, filename)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
