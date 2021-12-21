"""Plots average model profiles"""
import os
import datetime as dt
import numpy as np

from icepolcka_utils.data_base import CRSIMDataBase, TracksDataBase
from icepolcka_utils.geo import get_target_distance
from icepolcka_utils.utils import load_config


PERIODS = [
    [dt.datetime(2019, 5, 28, 11, 20), dt.datetime(2019, 5, 28, 14, 5)],
    [dt.datetime(2019, 6, 21, 14, 40), dt.datetime(2019, 6, 21, 17, 25)],
    [dt.datetime(2019, 7, 1, 11, 20), dt.datetime(2019, 7, 1, 16, 50)],
    [dt.datetime(2019, 7, 7, 9, 20), dt.datetime(2019, 7, 7, 15, 10)],
    [dt.datetime(2019, 7, 8, 9), dt.datetime(2019, 7, 8, 14)]
    ]


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


def get_cfads(tracks, crsim_data, max_range, mp, variables, sites, heights, hm, bin_limits):

    poldi_stacked = {}
    mira_stacked = {}
    isen_stacked = {}

    for var in variables:
        poldi_stacked[var] = [None for i in range(len(heights))]
        mira_stacked[var] = [None for i in range(len(heights))]
        isen_stacked[var] = [None for i in range(len(heights))]

    # Loop through all tracks
    for track in tracks:
        print(track['date'])
        tracks_df = load_tracks(track)

        # Loop through all cells
        for scan, scan_df in tracks_df.groupby(level=0):

            # Check if time is within periods of interest

            scan_time = dt.datetime.strptime(str(scan_df['time'].values[0]),
                                             '%Y-%m-%dT%H:%M:%S.%f000')

            if not np.any([p[0] <= scan_time <= p[1] for p in PERIODS]):
                continue

            new_scan = True

            # Loop through all cells
            for cell, cell_df in scan_df.iterrows():

                # Check if cell is within mira range
                mira_d = get_target_distance(sites['Mira35'], (cell_df['lon'],
                                                               cell_df['lat']))
                if mira_d > max_range:
                    continue

                # If new scan, get corresponding crsim data
                if new_scan:
                    data_isen = crsim_data.get_closest_data(
                        scan_time, mp_id=mp, radar='Isen', hm=hm
                        )
                    if data_isen['time'] - scan_time > dt.timedelta(
                            seconds=300):
                        print('No Isen CRSIM Data found for time step: ',
                              scan_time)
                        exit()
                    data_isen = data_isen.load()
                    data_poldi = crsim_data.get_closest_data(
                        scan_time, mp_id=mp, radar='Poldirad', hm=hm
                        )
                    data_mira = crsim_data.get_closest_data(
                        scan_time, mp_id=mp, radar='Mira35', hm=hm
                        )
                    if data_poldi['time'] - scan_time > dt.timedelta(
                            seconds=300):
                        print('No Poldi CRSIM data found for time step: ',
                                scan_time)
                        exit()
                    if data_mira['time'] - scan_time > dt.timedelta(
                            seconds=300):
                        print('No Mira CRSIM Data found for time step: ',
                                scan_time)
                        exit()
                    data_poldi = data_poldi.load()
                    data_mira = data_mira.load()

                # Mask everything that's not a convective cell
                cell_mask = cell_df['mask']

                # Calculate histograms for each variable at each height
                for var in variables:
                    if var == 'DWR':
                        var_data = 'Zhh'
                    elif var == 'DWR_corr':
                        var_data = 'Zhh_corr'
                    else:
                        var_data = var
                    isen_masked = np.where(
                        cell_mask, data_isen[var_data].values, np.nan
                        )
                    poldi_masked = np.where(
                        cell_mask, data_poldi[var_data].values, np.nan
                        )
                    mira_masked = np.where(
                        cell_mask, data_mira[var_data].values, np.nan
                        )
                    if var == 'DWR' or var == 'DWR_corr':
                        poldi_masked = poldi_masked - mira_masked
                        mira_masked = poldi_masked
                    bins = get_bins(bin_limits[var])
                    for i in range(len(heights)):
                        isen_hist = np.histogram(isen_masked[i], bins=bins)[0]
                        poldi_hist = np.histogram(poldi_masked[i], 
                                                    bins=bins)[0]
                        mira_hist = np.histogram(mira_masked[i],
                                                    bins=bins)[0]
                        if isen_stacked[var][i] is None:
                            isen_stacked[var][i] = isen_hist
                        else:
                            isen_stacked[var][i] += isen_hist
                        if poldi_stacked[var][i] is None:
                            poldi_stacked[var][i] = poldi_hist
                            mira_stacked[var][i] = mira_hist
                        else:
                            poldi_stacked[var][i] += poldi_hist
                            mira_stacked[var][i] += mira_hist
                new_scan = False

    return poldi_stacked, mira_stacked, isen_stacked


def make_folders(cfad_output, mp):
    radars = ['Mira35', 'Poldirad', 'Isen']
    outputs = []
    for radar in radars:
        output = cfad_output + os.sep + 'MP' + str(mp) + os.sep + radar + os.sep
        if not os.path.exists(output):
            os.makedirs(output)
        outputs.append(output)
    return outputs


def main(cfg_file):
    print("Starting main")
    variables = ["Zhh", "Zdr", "DWR", "Kdp", "Adp", "Ah"]
    cfg = load_config(cfg_file)
    cfad_output = cfg['output']['CFADs'] + os.sep + "HM"
    heights = np.array(cfg['WRFGrid'])*1000  # WRFGrid config in [km]
    tracks = get_tracks(cfg['data']['TRACKS'], cfg['database']['TRACKS'],
                        cfg['update'], cfg['recheck'], cfg['start'], cfg['end'],
                        cfg['mp'])
    with CRSIMDataBase(cfg['data']['CRSIM'], cfg['database']['CRSIM'],
                       update=cfg['update'], recheck=cfg['recheck']) \
            as crsim_db:

        poldi, mira, isen = get_cfads(tracks, crsim_db, cfg['max_r'], cfg['mp'],
                                      variables, cfg['sites'], heights, 
                                      cfg['hm'], cfg['bins'])

        # Make output folder
        mira_dic, poldi_dic, isen_dic = make_folders(cfad_output, cfg['mp'])

        # Plot data
        for var in variables:
            np.save(mira_dic + var + '_' + cfg['hm'], np.array(mira[var]))
            np.save(poldi_dic + var + '_' + cfg['hm'], np.array(poldi[var]))
            np.save(isen_dic + var + '_' + cfg['hm'], np.array(isen[var]))


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)