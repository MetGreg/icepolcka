"""Plot precipitation histograms

Plots a simple histogram for the precipitation as simulated by WRF directly for
several different microphysics schemes. The data was precalculated. This
script just reads the json files containing the precalculated precipitation.

"""
import json
import os
import matplotlib.pyplot as plt

from icepolcka_utils.utils import load_config, make_folder

MPS = [8, 28, 10, 30, 50]


def init_dict(mps):
    """Initialize histogram container

    Initializes the histogram dictionary by creating a dictionary with a key
    for each microphysics scheme and a value initialized at 0 that is a
    counter for the simulated precipitation.

    Args:
        mps (list): WRF IDs of microphysics schemes.

    Returns:
        dict:
            Initialized histogram container.

    """
    print("Initializing histogram container")
    total_precip = {}
    for mp in mps:
        total_precip[mp] = 0
    return total_precip


def plot_hist(precip, legend, filename):
    """Plot histogram

    Plots the precipitation histogram.

    Args:
        precip (dict): Total precipitation [m³] for each microphysics scheme.
        legend (dict): Legend names.
        filename (str): Output file name.

    """
    mps = precip.keys()
    precip_data = precip.values()
    label = [legend[mp] for mp in mps]
    plt.bar(label, precip_data)
    plt.ylabel("Total precipitation (m³)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def load_data(filepath):
    """Load data

    Loads data from a json file.

    Args:
        filepath (str): Path to data file.

    Returns:
        dict:
            Loaded data.

    """
    with open(filepath, "r") as f:
        data = json.load(f)
    return data


def main():
    print("Starting main")
    cfg = load_config()
    total_precip = init_dict(MPS)
    all_file = make_folder(cfg['output']['PRECIP'] + os.sep + "plots") \
        + "all.png"
    day_precip = {}
    data_path = cfg['output']['PRECIP'] + os.sep + "data" + os.sep
    for file in os.listdir(data_path):
        day = file.split('.')[0]
        print("Date: ", day)
        data = load_data(data_path + file)
        for mp, precip in data.items():
            total_precip[int(mp)] += precip
            day_precip[int(mp)] = precip
        day_file = cfg['output']['PRECIP'] + os.sep + "plots" + os.sep + day \
            + ".png"
        plot_hist(day_precip, cfg['legend'], day_file)
    plot_hist(total_precip, cfg['legend'], all_file)


if __name__ == "__main__":
    main()
