"""Plot hiw statistics as a panel plot

The number of days/files that are expected to be loaded is defined in the beginning as a global
variable 'EXP_FILES'. This variable must be adjusted to the actual days that you want to plot. This
is a sanity check, to see if the correct number of data files is loaded.

The left column and right columns will be frequency and area of HIW-events respectively.
First row: reflectivity based statistics in 1.5 km altitude.
Second row: mixing ratio based statistics in 1.5 km altitude.
Third row: mixing ratio based statistics at surface.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    output: HIW
      - The path to the precalculated HIW statistics
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)

"""
import os
import pathlib

import datetime as dt
import numpy as np
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

from icepolcka_utils import hiw, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
STATS = ["area", "frequency"]
WRF_THRESHS = [0.000001, 0.000002, 0.000005, 0.00001, 0.00002, 0.00005, 0.0001, 0.0002, 0.0005,
               0.001, 0.002, 0.005, 0.01]
EXP_FILES = 1
WRF_HMS = ["graupel", "rain"]
HMC_HMS = ["rain", "hail_graupel"]
HMC_THRESHS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
LEGEND = {
    8: "Thompson 2-mom",
    28: "Thompson aerosol-aware",
    10: "Morrison 2-mom",
    30: "Spectral Bin",
    50: "P3",
    'Obs': "Observation",
    'DWD': "Observation"
    }


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    thresh_dict = {
        'hmc': _get_hmc_stats(cfg, height=16),
        'wrf': _get_wrf_stats(cfg, height=7),
        'wrf_sfc': _get_wrf_stats(cfg, height=0)
        }
    _plot_panel(thresh_dict, "rain")
    _plot_panel(thresh_dict, "hail")


def _get_colors():
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = list(prop_cycle.by_key()['color'][:6])
    orange = colors[1]
    green = colors[2]
    colors[1], colors[2] = green, orange
    colors[-1] = "black"
    colors_gen = (p for p in colors)
    return colors_gen


def _create_subplots():
    fig = plt.figure(figsize=(12, 12))
    grid_spec = fig.add_gridspec(3, 2, hspace=0.25, wspace=0.15)
    axes = grid_spec.subplots()
    return fig, axes


def _adjust_hm_name(hm_name, method):
    if hm_name == "hail":
        if method == "wrf":
            hm_adjusted = "graupel"
        else:
            hm_adjusted = "hail_graupel"
    else:
        hm_adjusted = hm_name
    return hm_adjusted


def _create_legend(axs):
    handles, labels = axs.ravel()[0].get_legend_handles_labels()
    line_min = Line2D([0], [0], label="Minimum", color="k", linestyle="-.")
    line_mean = Line2D([0], [0], label="Mean", color="k")
    line_max = Line2D([0], [0], label="Maximum", color="k", linestyle="--")
    handles.extend([line_min, line_mean, line_max])
    return handles, labels


def _plot_panel(thresh_dict, hm_name):
    fig, axs = _create_subplots()
    threshs = [thresh_dict['hmc'], thresh_dict['hmc'], thresh_dict['wrf'], thresh_dict['wrf'],
               thresh_dict['wrf_sfc'], thresh_dict['wrf_sfc']]
    methods = ["hmc", "hmc", "wrf", "wrf", "wrf", "wrf"]
    stats = ["frequency", "area", "frequency", "area", "frequency", "area"]
    heights = [1, 1, 1, 1, 0, 0]
    i = 0
    for cfg in zip(threshs, methods, stats, heights):
        what = {'hm_name': _adjust_hm_name(hm_name, cfg[1]), 'method': cfg[1], 'stat': cfg[2],
                'height': cfg[3]}
        _plot(cfg[0], what, axs.ravel()[i])
        i += 1
    handles, _ = _create_legend(axs)
    fig.legend(handles=handles, loc=(0.25, 0.91), ncol=3)
    plt.savefig(hm_name + ".png", bbox_inches="tight")


def _load_stats(stats_class, cfg, height):
    stats_obj = stats_class(cfg, height=height)
    path = pathlib.Path(stats_obj.file_path)
    file_number = 0
    for file in os.listdir(path.parent):
        file_split = str(file).split("_")  # Format always: %Y-%m-%d_000000_TO_%Y-%m-%d_235959.npy
        date = file_split[0]  # In my data: start and end date the same for one file
        date_dt = dt.datetime.strptime(date, "%Y-%m-%d")
        if cfg['start'] <= date_dt <= cfg['end']:
            stats_obj.load_stats(str(path.parent) + os.sep + str(file))
            file_number += 1
    stats_obj.get_more_stats()
    return stats_obj, file_number


def _get_wrf_stats(cfg, height):
    cfg['method'] = "wrf"
    cfg['source'] = "MODEL"
    threshs = {}
    for mp_id in [8, 28, 10, 30, 50]:
        cfg['mp'] = mp_id
        stat, file_number = _load_stats(hiw.WRFStats, cfg, height)
        assert file_number == EXP_FILES, "Number of files is not as expected for wrf with mp: " + \
                                         str(mp_id) + ". Expected: " + str(EXP_FILES) \
                                         + " actual number: " + str(file_number)
        threshs[mp_id] = _get_stats(stat, WRF_THRESHS, WRF_HMS)
    return threshs


def _get_hmc_stats(cfg, height):
    cfg['method'] = "Dolan"
    threshs = {}
    for mp_id in [8, 28, 10, 30, 50, "DWD"]:
        cfg['source'] = "MODEL"
        cfg['mp'] = mp_id
        if mp_id == "DWD":
            cfg['mp'] = str(None)
            cfg['source'] = "DWD"
        stat, file_number = _load_stats(hiw.DolanStats, cfg, height)
        assert file_number == EXP_FILES, "Number of files is not as expected for hmc with MP: " + \
                                         str(mp_id) + ". Expected: " + str(EXP_FILES) \
                                         + " actual number: " + str(file_number)
        threshs[mp_id] = _get_stats(stat, HMC_THRESHS, HMC_HMS)
    return threshs


def _get_freq(area):
    freq_list = []
    for i in range(0, len(area), 288):
        day = area[i: i+288]
        freq = np.where(day > 0)
        freq_list.append(len(freq[0]))
    data = (np.min(freq_list), np.mean(freq_list), np.max(freq_list))
    return data


def _get_stats(stat, threshs, hms):
    thresh_dict = {}
    for hm_name in hms:
        thresh_dict[hm_name] = {}
        thresh_dict[hm_name]["area"] = {}
        thresh_dict[hm_name]["frequency"] = {}
        thresh_dict[hm_name]["area"][0] = []
        thresh_dict[hm_name]["area"][50] = []
        thresh_dict[hm_name]["area"][100] = []
        thresh_dict[hm_name]["frequency"][0] = []
        thresh_dict[hm_name]["frequency"][50] = []
        thresh_dict[hm_name]["frequency"][100] = []
        x_axis = []
        idx = None
        for thresh in threshs:
            x_axis.append(thresh)
            area = stat.stats["area"][hm_name][thresh]
            if idx is None:
                idx = np.where(area > 0)
            data = (np.nan, np.nan, np.nan)
            if len(idx[0]) != 0:
                data = (np.min(area[idx]), np.mean(area[idx]), np.max(area[idx]))
            thresh_dict[hm_name]["area"][0].append(data[0])
            thresh_dict[hm_name]["area"][50].append(data[1])
            thresh_dict[hm_name]["area"][100].append(data[2])
            freq = _get_freq(area)
            thresh_dict[hm_name]["frequency"][0].append(freq[0])
            thresh_dict[hm_name]["frequency"][50].append(freq[1])
            thresh_dict[hm_name]["frequency"][100].append(freq[2])
    return thresh_dict


def _get_method_data(method):
    cfg = {}
    if method == "wrf":
        cfg = {
            'hms': WRF_HMS,
            'x_axis': WRF_THRESHS,
            'xlabel': "Mixing ratio threshold (kg/kg)",
            'mp_ids': [8, 28, 10, 30, 50]
            }
    if method == "hmc":
        cfg = {
            'hms': HMC_HMS,
            'x_axis': HMC_THRESHS,
            'xlabel': "Reflectivity threshold (dBZ)",
            'mp_ids': [8, 28, 10, 30, 50, "DWD"]
            }
    return cfg


def _get_label(stat, hm_name, height):
    if stat == "area":
        label = "Area (km²) covered by " + hm_name
    else:
        label = "Daily hours of " + hm_name
    if height == 0:
        height_addon = " at surface"
    else:
        height_addon = " at " + str(height) + "km"
    return label + height_addon


def _norm(mp_data, stat):
    if stat == "frequency":  # Normalize frequency to hours (12 steps per hour)
        norm = 12
    else:
        norm = 1

    mp_data[0] = np.array(mp_data[0]) / norm
    mp_data[50] = np.array(mp_data[50]) / norm
    mp_data[100] = np.array(mp_data[100]) / norm
    return mp_data


def _plot(data, what, axis):
    plot_cfg = _get_method_data(what['method'])
    plot_cols = _get_colors()
    markers = (m for m in ["x-", "o-", "v-", "s-", "p-", "D-"])
    for mp_id in plot_cfg['mp_ids']:
        col = next(plot_cols)
        mp_data = data[mp_id][what['hm_name']][what['stat']]
        mp_data = _norm(mp_data, what['stat'])
        axis.plot(plot_cfg['x_axis'], mp_data[50], next(markers), color=col,
                  label=LEGEND[mp_id])
        axis.plot(plot_cfg['x_axis'], mp_data[0], "-.", color=col, linewidth=1)
        axis.plot(plot_cfg['x_axis'], mp_data[100], "--", color=col, linewidth=1)
    if what['hm_name'] == "rain" and what['method'] == "hmc":
        axis.axvline(x=41.2, color="gray", linestyle="-")
        axis.axvline(x=44.3, color="gray", linestyle="-")
        axis.axvline(x=47, color="gray", linestyle="-")

    if what['hm_name'] == "hail_graupel" and what['method'] == "hmc":
        axis.set_xlim(35, None)
    if what['stat'] == "area":
        axis.set_ylim(0, 1900)
        axis.set_yscale("symlog", linthresh=10, subs=[2, 3, 4, 5, 6, 7, 8, 9])
    else:
        axis.set_ylim(0, 24.5)
    if what['method'] == "wrf":
        axis.set_xscale("log")
    ylabel = _get_label(what['stat'], what['hm_name'], what['height'])
    axis.set_ylabel(ylabel)
    axis.set_xlabel(plot_cfg['xlabel'])


if __name__ == "__main__":
    _main(CONFIG_FILE)
