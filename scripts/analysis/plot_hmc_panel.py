"""Plot HMC data for a specific time stamp as a panel plot

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg data path
    database: RG
      - The rg database file path
    data: HMC
      - The hmc data path
    database: HMC
      - The hmc database file path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    update
      - Whether to update the database with new files

"""
import numpy as np
from matplotlib import colors
import matplotlib.pyplot as plt

from icepolcka_utils import utils, plots
from icepolcka_utils.database import algorithms, interpolations, main

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
HEIGHT = 16
LEGEND = {
    8: "Thompson 2-mom",
    28: "Thompson aerosol-aware",
    10: "Morrison 2-mom",
    30: "Spectral Bin",
    50: "P3",
    'DWD': "Observation",
    'Obs': "Observation"
    }


def _get_title(data):
    if data.source == "MODEL":
        title = LEGEND[data.MP_PHYSICS]
    else:
        title = LEGEND[data.source]
    return title


def _create_plot_cfg(data, x_grid, y_grid):
    hid_colors = ["LightBlue", "MediumBlue", "DarkOrange", "LightPink", "Cyan", "DarkGray", "Lime",
                  "Yellow", "Red", "Fuchsia"]
    cmap = colors.ListedColormap(hid_colors)
    title = _get_title(data)
    image_cfg = {'vmin': 1, 'vmax': 10, 'cmap': cmap, 'title': title}
    grid_cfg = {'x_axis': x_grid, 'y_axis': y_grid, 'width': 0.5}
    fonts_cfg = {'small_city': 6, 'big_city': 8, 'xticks': 8, 'yticks': 8, 'title': 8}
    plot_cfg = plots.PlotConfig(image_cfg=image_cfg, grid_cfg=grid_cfg, fonts_cfg=fonts_cfg)
    return plot_cfg


def _plot_subplots(axs, data, grid):
    """Plot all subplots

    Plots a panel plot with each of the subplots.

    Args:
        axs (numpy.ndarray): Array containing the axes for all subplots.
        data (list): List of HMC data.
        grid (list): List of corresponding lon/lat grids.

    Returns:
        matplotlib.collections.QuadMesh:
            Matplotlib pcolormesh image.

    """
    i = 0
    x_axis, y_axis = [3, 4, 5], [0, 3]
    for axi in axs.ravel():
        x_grid = i in x_axis
        y_grid = i in y_axis
        plot_cfg = _create_plot_cfg(data[i], x_grid, y_grid)
        img = plots.plot_munich(data[i]['HID'].values[HEIGHT], grid[i], plot_cfg, axis=axi)
        i += 1
    return img


def _get_handles(src, cfg):
    """Load data files

    Loads correct rg data, depending on observation or model data is wanted.

    """
    cfg['mp'] = src
    if src == "Obs":
        cfg['source'] = "DWD"
    else:
        cfg['source'] = "MODEL"
    rg_handles = main.get_handles(interpolations.RGDataBase, cfg, "RG", mp_id=src,
                                  source=cfg['source'])
    hmc_handles = main.get_handles(algorithms.HMCDataBase, cfg, "HMC", mp_id=src,
                                   source=cfg['source'])
    rg_data = rg_handles[0].load()
    hmc_data = hmc_handles[0].load()
    return rg_data, hmc_data


def _finish_plot(fig, img, filename):
    """Last plot settings

    Labels and saves the plot.

    Args:
        fig (matplotlib.figure.Figure): Figure with the image.
        img (matplotlib.collections.QuadMesh): Image containing a subplot.
        filename (str): Output file name.

    """
    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.98, 0.15, 0.02, 0.7])
    cbar = plt.colorbar(img, cax=cbar_ax)
    n_clusters = 11
    tick_locs = (np.arange(n_clusters) + 0.6)*(n_clusters-1)/n_clusters
    cbar.set_ticks(tick_locs)
    cbar.set_ticklabels(["No precip", "Drizzle", "Rain", "Ice Crystals", "Aggregates",
                         "Wet Snow", "Vertical Ice", "LD Graupel", "HD Graupel", "Hail",
                         "Big Drops / \n Melting hail"])
    cbar.ax.set_ylabel("")
    cbar.ax.tick_params(length=0)

    # Save figure
    plt.tight_layout()
    plt.savefig(filename, bbox_inches="tight", dpi=300)
    plt.close()


def _loop(cfg, filename):
    fig, axs = plots.create_subplots()
    rg_data_list, hmc_data_list = [], []
    for mp_id in [8, 28, 10, 30, 50, "Obs"]:
        rg_data, hmc_data = _get_handles(mp_id, cfg)
        rg_data_list.append(rg_data)
        hmc_data_list.append(hmc_data)
    img = _plot_subplots(axs, hmc_data_list, rg_data_list)
    _finish_plot(fig, img, filename)


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    assert cfg['start'].replace(second=0) == cfg['end'].replace(second=0), "Only one time step " \
                                                                           "possible"
    _loop(cfg, filename="hmc.png")


if __name__ == "__main__":
    _main(CONFIG_FILE)
