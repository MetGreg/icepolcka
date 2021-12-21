"""Script to visualize cell tracks

Cell tracks are plotted for the configured data. Cell tracks are defined for
each day separately. That's why the configured start and end time in this
script must be of the same day.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import pytz
import numpy as np

from icepolcka_utils.colormaps import get_precip_cmap
from icepolcka_utils.data_base import RGDataBase, TracksDataBase
from icepolcka_utils.grid import get_pyart_grids
from icepolcka_utils.plots import plot_tracks
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


def get_grid_handles(grid_path, db, update, recheck, start, end, source, mp,
                     radar):
    """Get RegularGrid data

    Args:
        grid_path (str): Path to RegularGrid data.
        db (str): Path to RegularGrid data base.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime): Start time [UTC] of configured time range.
        end (datetime.datetime): End time [UTC] of configured time range.
        source (str): Whether to find 'DWD' or 'MODEL' data.
        mp (int): WRF ID of a microphysics scheme to be returned.
        radar (str): Name of simulated radar.

    Raises:
        AssertionError: When the length of the handles equals 0.

    Returns:
        list:
            List of ResultHandles corresponding to the RegularGrid data.

    """
    print("Getting Regular grids")
    with RGDataBase(grid_path, db, update=update, recheck=recheck) as grid_db:
        grid_handles = grid_db.get_data(start, end, source=source, mp_id=mp,
                                        radar=radar)
    assert len(grid_handles) > 0, "No grid handles found for this period"
    return grid_handles


def get_tracks(tracks_path, db, update, recheck, start, end, source, mp, radar,
               track_params):
    """Get tracks

    Get the tracks data. Only works on daily basis.

    Args:
        tracks_path (str): Path to tracks data.
        db (str): Path to tracks data base.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime): Start time [UTC] of configured time range.
        end (datetime.datetime): End time [UTC] of configured time range.
        source (str): Whether 'DWD' or 'MODEL' data is returned.
        mp (int): WRF ID of a microphysics scheme to be returned.
        radar (str): Radar name.
        track_params (dict): TINT tracking parameters.

    Raises:
        AssertionError: When other than 1 track handle is found for the
            configured time range.

    Returns:
        CellTracks:
            CellTracks object that includes the loaded tracks.

    """
    print("Getting tracks")
    with TracksDataBase(tracks_path, db, update=update,
                        recheck=recheck) as tracks_data:
        handles = tracks_data.get_data(start, end, source=source, mp_id=mp,
                                       radar=radar)
    assert len(handles) == 1, "Only daily analysis possible, found: " \
                              + str(len(handles))

    # Load tracks and apply possible isolated filter
    tracks = handles[0].load()
    tracks = tracks.to_dataframe()
    tracks = tracks.dropna()
    tracks = tracks[(tracks['time'] >= start) & (tracks['time'] <= end)]
    tracks_obj = CellTracks(params=track_params)
    tracks_obj.tracks = tracks
    return tracks_obj


def plot_euler_tracks(tracks_obj, grids, extent, output):
    """Plot tracks

    Plots tracks in an euler way.

    Args:
        tracks_obj (CellTracks): CellTracks object that includes the loaded
            tracks.
        grids (list): List of corresponding PyArtGrids.
        extent (list): Extent of domain (lon_min, lon_max, lat_min, lat_max)
        output (str): Path to output folder.

    """
    print("Plotting tracks")
    cmap = get_precip_cmap()
    levels = np.arange(0, 51, 2)
    cities = ["München", "Augsburg"]
    plot_tracks(tracks_obj, grids, extent, levels, cities, output, cmap=cmap, cell_text=True)


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    start = cfg['start'].replace(tzinfo=pytz.utc)
    end = cfg['end'].replace(tzinfo=pytz.utc)
    mp, radar = get_data_base(cfg)
    mask = cfg['masks']['Height'] + os.sep + radar + ".npy"
    mask = np.load(mask)
    grid_handles = get_grid_handles(cfg['data']['RG'], cfg['database']['RG'],
                                    cfg['update'], cfg['recheck'], start, end,
                                    cfg['source'], mp, radar)
    grids = get_pyart_grids(grid_handles, mask)
    tracks_obj = get_tracks(cfg['data']['TRACKS'], cfg['database']['TRACKS'],
                            cfg['update'], cfg['recheck'], start, end,
                            cfg['source'], mp, radar, cfg['tracking'])
    output = cfg['output']['TRACKS'] + os.sep + cfg['source'] + os.sep
    output_euler = make_folder(output, mp, radar, date=start)
    plot_euler_tracks(tracks_obj, grids, cfg['extent']['Munich'], output_euler)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
