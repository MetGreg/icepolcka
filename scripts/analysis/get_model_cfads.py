"""Calculate model CFADs

Creates Contoured Frequency by Altitude Distribution (CFADs) for both radars,
Mira-35 and Poldirad. This script does not plot anything, but instead calculates
the frequency distribution and saves this to a numpy array. The height steps are
predefined using height levels from a specific WRF simulation. A histogram of
the reflectivity (or other variable) distribution for each of these height steps
is calculated and stacked to one big numpy array that is saved. The date range,
mp scheme and other settings are defined using the configuration file.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import datetime as dt
import numpy as np

from icepolcka_utils.data_base import RGDataBase, TracksDataBase
from icepolcka_utils.geo import get_target_distance
from icepolcka_utils.utils import load_config, make_folder


PERIODS = [
    [dt.datetime(2019, 5, 28, 11, 20), dt.datetime(2019, 5, 28, 14, 5)],
    [dt.datetime(2019, 6, 21, 14, 40), dt.datetime(2019, 6, 21, 17, 25)],
    [dt.datetime(2019, 7, 1, 11, 20), dt.datetime(2019, 7, 1, 16, 50)],
    [dt.datetime(2019, 7, 7, 9, 20), dt.datetime(2019, 7, 7, 15, 10)],
    [dt.datetime(2019, 7, 8, 9), dt.datetime(2019, 7, 8, 14)]
    ]
CENTER = False


def get_tracks(path, db, update, recheck, start, end, mp):
    """Get tracks data

    Gets the tracks handles from the TracksDataBase corresponding to
    the data within the time range, and microphysics that was configured.

    Args:
        path (str): Path to Tracks data.
        db (str): Path to Tracks data base file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List of all data handles corresponding to configured input.

    """
    print("Getting Tracks")
    with TracksDataBase(path, db, update=update,
                        recheck=recheck) as tracks_data:
        tracks = tracks_data.get_data(start, end, source="MODEL", mp_id=mp,
                                      radar="Isen")
    return tracks


def prepare_dicts(variables, heights):
    """Prepare dictionary containers

    Prepares two dictionaries, one for Mira-35, one for Poldirad. The
    dictionaries have entries for each variable. The corresponding dictionary
    values are lists that have the same length as the heights array and are
    filled with None.

    These dictionaries will later be filled with histograms, one for each
    height. This is then the CFAD array.

    Args:
        variables (list): List of variable names.
        heights (list or numpy.ndarray): List of height steps [m].

    Returns:
        (dict, dict):
            1) Container for Poldirad CFADs.
            2) Container for Mira-35 CFADs.

    """
    poldi_stacked = {}
    mira_stacked = {}

    for var in variables:
        poldi_stacked[var] = [None for i in range(len(heights))]
        mira_stacked[var] = [None for i in range(len(heights))]
    return poldi_stacked, mira_stacked


def load_tracks(track):
    """Load tracks data

    Loading the tracks data and transforming it to a pandas data frame.

    Args:
        track (ResultHandle): Handle that contains track data.

    Returns:
        pandas.core.frame.DataFrame:
            Loaded tracks data.

    """
    tracks_data = track.load()
    tracks_df = tracks_data.to_dataframe()
    tracks_df = tracks_df.dropna()
    return tracks_df


def get_rg_data(rg_data, time, mp):
    """Get RegularGrid data

    Given a time and a MP scheme ID, this function returns the loaded
    RegularGrid data sets.

    Args:
        rg_data (RGDataBase): Opened RegularGrid data base.
        time (datetime.datetime): Time step [UTC] at which the closest
            RegularGrid data will be returned.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        (xarray.core.dataset.Dataset, xarray.core.dataset.Dataset):
            1) Loaded dataset of Poldirad RegularGrid data.
            2) Loaded dataset of Mira35 RegularGrid data.

    """
    poldi_data = rg_data.get_closest_data(time, mp_id=mp, radar="Poldirad")
    if poldi_data['time'] - time > dt.timedelta(seconds=300):
        print("No Regular Grid for Poldirad found for time step: ", time)
        exit()
    mira_data = rg_data.get_closest_data(time, mp_id=mp, radar="Mira35")
    if mira_data['time'] - time > dt.timedelta(seconds=300):
        print("No Regular Grid for Mira-35 found for time step: ", time)
        exit()
    poldi_data = poldi_data.load()
    mira_data = mira_data.load()
    return poldi_data, mira_data


def get_var_key(var):
    """Get variable key

    When the Dual-wavelength "DWR" CFAD is created, the actual data key
    is "Zhh" (or "Zhh_corr"). This function returns the data key that
    corresponds to the current variable.

    Args:
        var (str): Variable name.

    Returns:
        str:
            Data key corresponding to variable name.

    """
    if var == "DWR":
        var_data = "Zhh"
    elif var == "DWR_corr":
        var_data = "Zhh_corr"
    else:
        var_data = var
    return var_data


def mask_data(data, cell_mask, height_mask):
    """Mask data

    Applies two masks onto the data. One for the cell location, that masks
    all grid boxes not within the cell. The other one masks everything that
    is not within the highest and lowest radar beam.

    Args:
        data (xarray.core.dataArray.DataArray): Data that will be masked.
        cell_mask (numpy.ndarray): Mask for the convective cell. True,
            if grid box is within convective cell.
        height_mask (numpy.ndarray): Height mask. True, if grid box is within
            highest and lowest radar beams.

    Returns:
        numpy.ndarray:
            Masked data. Everything that is masked is put to numpy.nan

    """
    masked_data = np.where(cell_mask, data.values, np.nan)
    masked_data = np.where(height_mask, masked_data, np.nan)
    return masked_data


def get_bins(bin_limits):
    """Get bin limits

    Reads the bin configuration and creates bins accordingly.

    Args:
        bin_limits (list): List of minimum bin, maximum bin and bin resolution.

    Returns:
        numpy.ndarray:
            Bins within the given range and with the given resolution.

    """
    xmin = bin_limits[0]
    xmax = bin_limits[1]
    steps = bin_limits[2]
    bins = np.arange(xmin, xmax + steps, steps)
    return bins


def stack_histograms(poldi_stacked, mira_stacked, poldi_data, mira_data, 
                     heights, heights_grid, bins, var):
    """Stack histogram container with new data

    The CFAD container are dictionaries with one key for each variable. The
    corresponding value is the CFAD for this variable: A numpy array with a
    histogram for each height. This function loops through all heights,
    calculates the histogram and adds it to the CFAD container. This is done
    for both radars, Mira-35 and Poldirad.

    Args:
        poldi_stacked (dict): Container for Poldirad CFADs. One key for each
            variable. Value must be a list/array of the same length as heights.
        mira_stacked (dict): Container for Mira-35 CFADs. One key for each
            variable. Value must be a list/array of the same length as heights.
        poldi_data (numpy.ndarray): 3D data array of Poldirad.
        mira_data (numpy.ndarray): 3D data array of Mira-35.
        heights (numpy.ndarray): Height steps of the CFADs.
        heights_grid (numpy.ndarray): Height steps of the RegularGrid input
            data.
        bins (numpy.ndarray): Bins that will be used for the histograms.
        var (str): Variable name.

    Returns:
        (dict, dict):
            1) Poldirad CFAD container, filled with the histograms for the
                given variable.
            2) Mira-35 CFAD container, filled with the histograms for the
                given variable.

    """
    for i in range(len(heights)):
        h = heights[i]
        h_grid = np.where(np.isclose(heights_grid, h))[0][0]
        poldi_hist = np.histogram(poldi_data[h_grid], bins=bins)[0]
        mira_hist = np.histogram(mira_data[h_grid], bins=bins)[0]
        if poldi_stacked[var][i] is None:
            poldi_stacked[var][i] = poldi_hist
            mira_stacked[var][i] = mira_hist
        else:
            poldi_stacked[var][i] += poldi_hist
            mira_stacked[var][i] += mira_hist

    return poldi_stacked, mira_stacked


def get_cfads(tracks, rg_data, variables, heights, sites, max_range,
              mp, bin_limits, poldi_mask, mira_mask):
    """Get CFAD array

    This function returns two dictionaries, one for Mira-35 and one for
    Poldirad. For each variable, the dictionaries contain a numpy array that
    consists, for each height step, of a histogram the variable values over a
    number of bins.

    The function loads the tracks for the day, loops through all scans and
    cells, finds the RegularGrid data that corresponds to the time step.
    Then, the Regular Grid data is masked so that only the grid boxes within
    the cell are considered and only grid boxes within the highest and lowest
    radar beam.

    Also, only time steps within the given PERIODS and cells within the Mira-35
    range are considered.

    Args:
        tracks (list): List of CellTracks ResultHandles.
        rg_data (RGDataBase): Data base of RegularGrid data.
        variables (list): Variable names.
        heights (list or numpy.ndarray): Height steps of the CFAD [m].
        sites (dict): Site coordinates (lon/lat/alt) of the radars.
        max_range (int): Maximum range of domain to consider [m].
        mp (int): WRF ID of microphysics scheme.
        bin_limits (dict): Minimum, maximum and resolution of the variable bins.
        poldi_mask (numpy.ndarray): Height mask of Poldirad. True, if within
            radar beams.
        mira_mask (numpy.ndarray): Height mask of Mira-35. True, if within
            radar beams.

    Returns:
        (dict, dict):
            1) Poldirad CFADs. For each variable, an array of histograms at
                each height step.
            2) Mira-35 CFADs. For each variable, an array of histograms at
                each height step.

    """
    poldi_stacked, mira_stacked = prepare_dicts(variables, heights)

    # Loop through all tracks
    for track in tracks:
        print(track['date'])
        tracks_df = load_tracks(track)

        # Loop through all cells
        for scan, scan_df in tracks_df.groupby(level=0):
            # Check if time is within periods of interest
            scan_time = dt.datetime.strptime(str(scan_df['time'].values[0]),
                                             "%Y-%m-%dT%H:%M:%S.%f000")
            if not np.any([p[0] <= scan_time <= p[1] for p in PERIODS]):
                continue

            # Loop through all cells
            print(scan_time)
            new_scan = True
            for cell, cell_df in scan_df.iterrows():
                # Check if cell is within mira range
                mira_d = get_target_distance(sites['Mira35'], (cell_df['lon'],
                                                               cell_df['lat']))
                if mira_d > max_range:
                    continue

                # If new scan, get corresponding rg data
                if new_scan:
                    poldi_data, mira_data = get_rg_data(rg_data, scan_time, mp)

                # Mask everything that's not a convective cell
                cell_mask = cell_df['mask']
                h_grid = poldi_data.height.values

                # Calculate histograms for each variable at each height
                for var in variables:
                    var_key = get_var_key(var)

                    if CENTER:
                        poldi_masked = poldi_data[var_key].copy()
                        poldi_masked[:] = np.nan
                        mira_masked = mira_data[var_key].copy()
                        mira_masked[:] = np.nan
                        x = int(np.round(cell_df['grid_x']))
                        y = int(np.round(cell_df['grid_y']))
                        poldi_masked[:, y, x] = poldi_data[var_key][:, y, x]
                        mira_masked[:, y, x] = mira_data[var_key][:, y, x]
                    else:
                        poldi_masked = mask_data(poldi_data[var_key], cell_mask,
                                                 poldi_mask)
                        mira_masked = mask_data(mira_data[var_key], cell_mask,
                                                mira_mask)
                    if var == "DWR" or var == "DWR_corr":
                        poldi_masked = poldi_masked - mira_masked
                        mira_masked = poldi_masked
                    bins = get_bins(bin_limits[var])
                    poldi_stacked, mira_stacked = stack_histograms(
                        poldi_stacked, mira_stacked, poldi_masked,
                        mira_masked, heights, h_grid, bins, var
                        )
                new_scan = False

    return poldi_stacked, mira_stacked


def save(output, mp, variables, poldi, mira):
    """Save CFADs

    Save CFAD arrays to numpy array.

    Args:
        output (str): Path to CFAD folder.
        mp (int): WRF ID of microphysics scheme.
        variables (list): List of variable names.
        poldi (dict): Poldirad CFADs. For each variable, an array of histograms
            at each height step.
        mira (dict): Mira-35 CFADs. For each variable, an array of histograms at
            each height step.

    """
    output = output + os.sep + "model" + os.sep
    poldi_output = make_folder(output, mp, "Poldirad")
    mira_output = make_folder(output, mp, "Mira35")
    for var in variables:
        np.save(poldi_output + var, np.array(poldi[var]))
        np.save(mira_output + var, np.array(mira[var]))


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    mira_mask = np.load(cfg['masks']['Height'] + os.sep + "Mira35.npy")
    poldi_mask = np.load(cfg['masks']['Height'] + os.sep + "Poldirad.npy")
    variables = ["Zhh", "Zhh_corr", "Zdr", "Zdr_corr", "DWR", "DWR_corr", "Kdp"]
    heights = np.array(cfg['WRFGrid'])*1000  # WRFGrid config in [km]
    tracks = get_tracks(cfg['data']['TRACKS'], cfg['database']['TRACKS'],
                        cfg['update'], cfg['recheck'], cfg['start'], cfg['end'],
                        cfg['mp'])
    with RGDataBase(cfg['data']['RG'], cfg['database']['RG'],
                    update=cfg['update'], recheck=cfg['recheck']) as rg_data:
        poldi, mira = get_cfads(
            tracks, rg_data, variables, heights, cfg['sites'], cfg['max_r'],
            cfg['mp'], cfg['bins'], poldi_mask, mira_mask
            )
    save(cfg['output']['CFADs'], cfg['mp'], variables, poldi, mira)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
