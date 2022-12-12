"""Plot psd

Creates a plot for the PSD data precalculated by the 'get_psd.py' script.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    output: PSD
      - The path to the precalculated PSD data
    output: PLOTS
      - The output path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)

"""
import os

import numpy as np
import matplotlib.pyplot as plt

from icepolcka_utils import schemes, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"

LEGEND = {
    8: "Thompson 2-mom",
    28: "Thompson aerosol-aware",
    10: "Morrison 2-mom",
    30: "Spectral Bin",
    50: "P3",
    }

Q_THRESHS = [0.000001, 0.00001, 0.0001, 0.001, 0.01]


def _plot(cfg, thresh_i, analysis):
    diameters = schemes.get_diameters()[17:]
    output_path = cfg['output']['PLOTS'] + os.sep + "psd" + os.sep + str(cfg['start']) + "_TO_" + \
        str(cfg['end']) + os.sep
    output = utils.make_folder(output_path) + str(Q_THRESHS[thresh_i]) + "_" + analysis + ".png"
    psd_path = cfg['output']['PSD'] + os.sep + str(cfg['start']) + "_TO_" + str(cfg['end']) + os.sep
    for mp_id in [8, 10, 28, 30, 50]:
        psd = np.load(psd_path + str(mp_id) + "_" + analysis + ".npy")
        plt.plot(diameters[:]*1000, psd[:, thresh_i], label=LEGEND[mp_id])
    plt.grid()
    plt.yscale("log")
    plt.ylabel("Particles (1/(kg * m))")
    plt.xlabel("Diameter (mm)")
    plt.legend()
    plt.savefig(output)
    plt.close()


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    for i, _ in enumerate(Q_THRESHS):
        _plot(cfg, i, "mean")


if __name__ == "__main__":
    _main(CONFIG_FILE)
