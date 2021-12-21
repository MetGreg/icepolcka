"""Plot cell statistics

Plots a histogram for each of the given variables over the configured time
range. Some settings are read from the configuration file.

For an explanation on how to use the configuration file, see the README file.

"""
import numpy as np
import matplotlib.pyplot as plt

from icepolcka_utils.data_base import TracksDataBase
from icepolcka_utils.geo import get_target_distance
from icepolcka_utils.utils import load_config, make_folder


VARIABLES = ["max_alt", "max"]
PLOT_CFG = {'max': {'xlabel': "Reflectivity (dBZ)",
                    'xlim': (30, 70),
                    'ylim': [0, 2400],
                    'steps': 5},
            'max_alt': {'xlabel': "Height (km)",
                        'xlim': (0, 15),
                        'ylim': [0, 2100],
                        'steps': 1}
            }

SRC = [8, 28, 10, 30, 50, "DWD"]


def init_plots(variables):
    """Initialize plots

    Initializes the plots by creating a figure and corresponding subplots for
    each variable.

    Args:
        variables (list): Variable names.

    Returns:
        dict:
            Initialized dictionary with a key for each variable and a
            tuple (fig, ax) as a value

    """
    print("Initializing plots")
    ax_dict = {}
    for var in variables:
        fig, ax = plt.subplots()
        ax_dict[var] = (fig, ax)
    return ax_dict


def get_colors():
    """Get colors

    Creates a generator object of colors that will be used for the histograms.

    Returns:
        generator:
            Colors that will be used for the histograms.

    """
    print("Getting colors")
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = [p for p in prop_cycle.by_key()['color'][:6]]
    orange = colors[1]
    green = colors[2]
    colors[1], colors[2] = green, orange
    colors[-1] = "black"
    colors_gen = (p for p in colors)
    return colors_gen


def get_tracks(db, src, start, end):
    """Get tracks data

    Get the tracks data, depending on the configured time range and data source.

    Args:
        db (TracksDataBase): Opened Cell-tracks data base.
        src (str or int): Data source. Either 'DWD' or th WRF ID of the
            microphysics scheme.
        start (datetime.datetime): Start time [UTC] of configured time range.
        end (datetime.datetime): End time [UTC] of configured time range.

    Returns:
        list:
            List of Tracks Resulthandles corresponding to configured input.

    """
    if src == "DWD":
        tracks = db.get_data(start, end, source=src)
    else:
        tracks = db.get_data(start, end, source="MODEL", mp_id=src,
                             radar="Isen")
    return tracks


def check_length(tracks, tracks_len=30):
    """Check length of tracks data

    If number of tracks does not equal the given length (default 30, for
    icepolcka data), raise an AssertionError.

    Args:
        tracks (list): List of Tracks Resulthandles.
        tracks_len (int): Expected number of tracks data.

    Raises:
        AssertionError: If length of tracks does not equal the expected length.

    """
    assert len(tracks) == tracks_len, "Wrong track numbers: " + str(len(tracks))


def init_container(variables):
    """Initialize histogram container

    Initializes the histogram dictionary by creating a dictionary with a key
    for each variable and an empty list that will be filled with the data later.

    Args:
        variables (list): Variable names.

    Returns:
        dict:
            Initialized histogram container.

    """
    container = {}
    for var in variables:
        container[var] = []
    return container


def load_tracks(track):
    """Load track data

    Loads the track data frame, transforms it to pandas data frame and
    removes the missing values.

    Args:
        track (ResultHandle): Track handle containing the CellTracks data
            that will be loaded.

    Returns:
        pandas.core.frame.DataFrame:
            Loaded tracks data frame.

    """
    tracks_data = track.load()
    tracks_df = tracks_data.to_dataframe()
    tracks_df = tracks_df.dropna()
    return tracks_df


def out_of_range(site, df, max_r):
    """Check if cell is out of Mira-35 range

    Given the Mira-35 site coordinates, the cell dataframe and the maximum
    range, this function returns TRUE, if the cell is out of Mira-35 range.

    Args:
        site (tuple): lon/lat/alt coordinates of Mira-35.
        df (pandas.core.series.Series): Dataframe containing the cell
            coordinates.
        max_r (int): Maximum Mira-35 range [m].

    Returns:
        bool:
            True, if cell is out of Mira-35 range.

    """
    mira_d = get_target_distance(site, (df['lon'], df['lat']))
    if mira_d > max_r:
        return True


def fill_container(variables, var_container, df):
    """Fill the histogram container

    The histogram container is a dictionary, with a key for each variable and a
    list as the corresponding value. This function appends the list with a
    new entry: The maximum value of the given variable at the given time step
    and of the given cell.

    Args:
         variables (list): Variable names.
         var_container (dict): Histogram container, a key for each variable.
         df (pandas.core.series.Series): DataFrame containing the CellTracks
             data of one convective cell.

    Returns:
        dict:
            Histogram container, where the data of the current cell has been
            appended.

    """
    for var in variables:
        var_container[var].append(np.nanmax(df[var]))
    return var_container


def calc_hist(db, src, start, end, variables, site, max_r):
    """Calculate histograms

    This function calculates histograms for the given variables within the
    given time period. The variables must be some TINT cell characteristics.
    The function just counts the frequency of these variables.

    Args:
        db (TracksDataBase): Database of CellTracks.
        src (str or int): Source of the data. Either a WRF mp-id or 'DWD'.
        start (datetime.datetime): Start time [UTC] of time period to be
            considered.
        end (datetime.datetime): End time [UTC] of time period to be considered.
        variables (list): List of variables for which a histogram is calculated.
        site (tuple): lon/lat/alt of Mira-35 site.
        max_r (int): Maximum range around Mira-35 to consider [m].

    Returns:
        dict:
           Histogram container filled with histogram data.

    """
    tracks = get_tracks(db, src, start, end)
    check_length(tracks)
    var_container = init_container(variables)
    cell_counter, big_cells = 0, 0
    for track in tracks:
        tracks_df = load_tracks(track)
        for scan, scan_df in tracks_df.groupby(level=0):
            for cell, df in scan_df.iterrows():
                if out_of_range(site, df, max_r):
                    continue
                if df['max_alt'] > 7:
                    big_cells += 1
                cell_counter += 1
                var_container = fill_container(variables, var_container, df)
    print("Total cells: ", str(cell_counter))
    print("Big cells: ", str(big_cells))
    return var_container


def plot_hist(variables, ax_dict, plot_cfg, var_container, label, col):
    """Plot histogram

    For each variable, this function plots a histogram.

    Args:
        variables (list): Variable names.
        ax_dict (dict): Container for the matplotlib axes. One key for each
            variable.
        plot_cfg (dict): Plot settings, like x- and y-limits and steps.
        var_container (dict): Container for the histogram data. One key for
            each variable.
        label (str): Label of the line.
        col (str): Color of the line.

    """
    for var in variables:
        ax = ax_dict[var][1]
        var_cfg = plot_cfg[var]
        xlim, ylim, steps = var_cfg['xlim'], var_cfg['ylim'], var_cfg['steps']
        bins = np.arange(xlim[0], xlim[1] + 1, steps)
        clip = np.clip(var_container[var], xlim[0], xlim[1])
        hist, edges = np.histogram(clip, bins=bins)
        centers = np.convolve(edges, np.ones(2)/2)[1:-1]
        ax.set_xlabel(var_cfg['xlabel'])
        ax.set_xticks(centers)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.plot(centers, hist, "o-", label=label, color=col)
        ax.set_ylabel("Absolute frequency")


def save_plot(ax_dict, output):
    """Save plot

    Args:
        ax_dict (dict): Container for the matplotlib axes. One key for each
            variable.
        output (str): Path to output file.

    """
    print("Saving plot")
    output = make_folder(output)
    for var, fig_tup in ax_dict.items():
        fig, ax = fig_tup
        ax.legend(loc=1)
        fig.savefig(output + str(var) + ".png")


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    ax_dict = init_plots(VARIABLES)
    colors = get_colors()
    with TracksDataBase(cfg['data']['TRACKS'], cfg['database']['TRACKS'],
                        update=cfg['update'], recheck=cfg['recheck']) as db:
        for src in SRC:
            print("MP: ", src)
            hist = calc_hist(db, src, cfg['start'], cfg['end'], VARIABLES,
                             cfg['sites']['Mira35'], cfg['max_r'])
            plot_hist(VARIABLES, ax_dict, PLOT_CFG, hist, cfg['legend'][src],
                      next(colors))
    save_plot(ax_dict, cfg['output']['HIST'])


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
