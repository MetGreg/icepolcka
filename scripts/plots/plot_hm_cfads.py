"""Plot CFADs

Plots the CFADs. The data is loaded from precalculated CFAD arrays. Some
settings are read from the configuration file.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from icepolcka_utils.utils import load_config, make_folder


#SRC = [8, 28, 10, 30]
SRC = [8, 28, 10, 30, 50]
#SRC = [50, 50, 50, 50, 50, 50]
VARIABLES = ["Zhh", "DWR", "Zdr", "Kdp", "Adp", "Ah"]
PLOT_LABELS = {
    'Zhh': "Reflectivity (dBZ)",
    'Zdr': "Differential reflectivity (dB)",
    'DWR': "Dual-wavelength ratio (dB)",
    'Kdp': "Specific differential phase (° km-1)",
    'Adp': "Specific differential attenuation (dB/km)",
    'Ah': "Attenuation (dB/km)"
    }

# Colorbar limits
VLIMS = {
    'Zhh': (10**-3, 3*10**(-1)),
    'Zdr': (10**(-4), 3*10**(-1)),
    'DWR': (10**-2, 10**(-1)),
    'Kdp': (10**(-4), 10**(-1)),
    'Adp': (10**(-4), 10**(-1)),
    'Ah': (10**(-4), 10**(-1)),
    }

# Annotation locations
LOCS = {
    8: (0.125, 0.883),
    28: (0.36, 0.883),
    10: (0.59, 0.883),
    30: (0.125, 0.48),
    50: (0.36, 0.48),
    "Obs": (0.59, 0.48),
    }

# These heights are WRF heights from the MP8 simulation at 01.07.2019 12 UTC
# Rounded to the next 100 m grid point
HEIGHTS = np.array([0.5, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2, 1.5, 1.7, 2.1, 2.4,
                    2.9, 3.3, 3.9, 4.4, 5, 5.7, 6.4, 7.1, 7.9, 8.7, 9.4,
                    10.1, 10.8, 11.5, 12.2, 12.9, 13.6, 14.2])


def create_subplots():
    """Create subplots

    Creates the figure and axis for the panel plot. One main figure and axis
    is created that will be used for labeling, and 6 smaller subplots are
    created that will be reserved for the CFAD plots.

    Returns:
        (matplotlib.Figure, numpy.ndarray, matplotlib.AxesSubplot):
            1) Matplotlib figure.
            2) Array of all axes.
            3) Main axis for labeling.

    """
    fig = plt.figure(figsize=(8, 5))
    gs = fig.add_gridspec(2, 3, hspace=0.1, wspace=0.1)
    #axs = gs.subplots(sharex="col", sharey="row")
    ax1 = plt.subplot(gs[0, 0])
    ax2 = plt.subplot(gs[0, 1])
    ax3 = plt.subplot(gs[0, 2])
    ax4 = plt.subplot(gs[1, 0])
    ax5 = plt.subplot(gs[1, 1])
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.setp(ax2.get_yticklabels(), visible=False)
    plt.setp(ax3.get_yticklabels(), visible=False)
    plt.setp(ax5.get_yticklabels(), visible=False)
    axs = np.array([ax1, ax2, ax3, ax4, ax5])
    #axs = np.array([ax1, ax2, ax3, ax4])
    return fig, axs


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


def get_cfad_data(src, cfad_path, radar, var, hm):
    """Get cfad data

    Gets the CFAD data path, depending on the data source, radar and variable
    and loads the data.

    Args:
        src (str or int): Data source. Either 'DWD' or th WRF ID of the
            microphysics scheme.
        cfad_path (str): Folder where the CFAD data arrays are located.
        radar (str): Radar name.
        var (str): Variable name.

    Returns:
        numpy.ndarray:
            Loaded CFAD data.

    """
    data_path = cfad_path + os.sep + "HM" + os.sep + "MP" + str(src) + os.sep + radar + os.sep \
        + str(var) + "_" + hm + ".npy"
    data = np.load(data_path)
    return data


def get_colormesh_lims(x):
    """Get colormesh heights

    Returns the center of each bin.

    Args:
        x (numpy.ndarray): Bins.

    Returns:
        list:
            Bins centered.

    """
    lims = [x[i] + (x[i + 1] - x[i])/2 for i in range(len(x) - 1)]
    lims.insert(0, x[0] - (x[1] - x[0])/2)
    lims.append(x[-1] + (x[-1] - x[-2])/2)
    return lims


def plot_subplot(ax, data, heights, bins, vmin, vmax):
    """Plot one subplot

    Plots a CFAD into one of the subplots. The frequency is a relative
    frequency that will be calculated in this function for each height.

    Args:
        ax (matplotlib.axes._subplots.AxesSubplot): Matplotlib axis.
        data (numpy.ndarray): CFAD data array.
        heights (numpy.ndarray): Heights array [km].
        bins (numpy.ndarray): Bin array.
        vmin (float): Minimum value range.
        vmax (float): Maximum value range.

    Returns:
        matplotlib.collections.QuadMesh:
            pcolormesh image of CFAD.

    """
    y = get_colormesh_lims(heights)
    data_rel = []
    for h in data:
        data_rel.append(h/np.nansum(h))
    img = ax.pcolormesh(bins, y[3:-3], np.array(data_rel)[3:-3], cmap="turbo",
                        norm=mcolors.LogNorm(vmin=vmin, vmax=vmax))
    return img


def plot_subplots(axs, sources, data_path, radar, var, bins, vmin, vmax, hm):
    """Plot all subplots

    Plots a CFAD for each of the subplots.

    Args:
        axs (numpy.ndarray): Array containing the axes for all subplots.
        sources (list): List of data sources. Either 'DWD' or WRF ID of
            microphysics scheme.
        data_path (str): Path to CFAD data array.
        radar (str): Radar name.
        var (str): Variable name.
        bins (numpy.ndarray): Bins within a given range and a given resolution.
        vmin (float): Minimum value range.
        vmax (float): Maximum value range.

    Returns:
        matplotlib.collections.QuadMesh:
            Matplotlib pcolormesh image.

    """
    i = 0
    for axi in axs.ravel():
        src = sources[i]
        data = get_cfad_data(src, data_path, radar, var, hm)
        img = plot_subplot(axi, data, HEIGHTS, bins, vmin=vmin, vmax=vmax)
        i += 1
    return img


def annotate(sources, fig, loc, legend):
    """Annotate subplots

    Each subplot gets a label.

    Args:
        sources (list): List of data sources. Either 'DWD' or WRF ID of
            microphysics scheme.
        fig (matplotlib.Figure): Figure that will be annotated.
        loc (dict): Location of plot annotations.
        legend (dict): Legend names.

    """
    for src in sources:
        fig.text(loc[src][0], loc[src][1], legend[src])


def finish_plot(fig, img, label, filename):
    """Last plot settings

    Labels and saves the plot.

    Args:
        fig (matplotlib.figure.Figure): Figure with the image.
        img (matplotlib.collections.QuadMesh): Image containing a CFAD.
        label (str): Label of x_axis.
        filename (str): Output file name.

    """
    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.82, 0.15, 0.02, 0.7])
    fig.colorbar(img, cax=cbar_ax, label="Relative frequency", extend="max")
    fig.text(0.06, 0.3, 'Height above NN (km)', rotation=90, fontsize=10)
    fig.text(0.37, 0.03, label, fontsize=10)
    plt.savefig(filename, bbox_inches="tight")
    plt.close()


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    hms = ["all", "rain", "graupel"]
    #hms = ["snow", "ice", "cloud"]
    #hms = ["unrimedice", "parimedice", "smallice"]
    for var in VARIABLES:
        print(var)
        bins = get_bins(cfg['bins'][var])
        for radar in ["Mira35", "Poldirad", "Isen"]:
            for hm in hms:
                filename = make_folder(cfg['output']['CFADs'] + os.sep + "plots"
                                       + os.sep + "hm" + os.sep + hm + os.sep,
                                       radar=radar) + var + ".png"
                fig, axs = create_subplots()
                img = plot_subplots(axs, SRC, cfg['output']['CFADs'], radar,
                                    var, bins, VLIMS[var][0], VLIMS[var][1], hm)
                annotate(SRC, fig, LOCS, cfg['legend'])
                finish_plot(fig, img, PLOT_LABELS[var], filename)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
