"""Calculate PSDs

This script calculates mean rain particle size distributions for a given time period. The
particle size distributions follow the corresponding microphysics scheme. The average particle size
distributions are calculated multiple times, for varying mixing ratio thresholds as defined in the
beginning of the script in the global variable 'Q_THRESHS'.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: WRF
      - The wrf data path
    database: WRF
      - The wrf database file path
    output: PSD
      - The output path
    masks: Distance
      - Path to the distance mask
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    update
      - Whether to update the database with new files

"""
import os

import numpy as np

from icepolcka_utils.database import models
from icepolcka_utils import schemes
from icepolcka_utils import utils

Z_IDX = 7  # 1.5 km round about

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"
Q_THRESHS = [0.000001, 0.00001, 0.0001, 0.001, 0.01]


def _mask_and_repeat(array, q_mask, d_mask):
    """Mask and repeat array

    This function expects two masks, a threshold mask and a distance mask. The threshold mask is a
    mask for multiple thresholds. The original data is masked with these threshold masks along a
    new dimension. This means the original data array is repeated 'n' times along a new dimension,
    where 'n' is the length of the threshold list. The given distance mask is also applied to the
    data array.

    Args:
        array (numpy.ndarray): Original data array.
        q_mask (numpy.ndarray): Mask for multiple thresholds. Shape must be (n, array.shape).
            True means below threshold.
        d_mask (numpy.ndarray): Distance mask. Must be same shape as array. True means outside
            Mira-35 range.

    Returns:
        (numpy.ndarray): Masked array. Shape: (n, array.shape).

    """
    array_rep = np.repeat(array[np.newaxis], len(q_mask), axis=0)  # Repeat array to length of mask
    array_masked = np.where(~q_mask, array_rep, np.nan)  # Add mixing ratio mask
    array_masked = np.where(~d_mask, array_masked, np.nan)  # Add distance mask
    return array_masked


def _calc_mean_psd(handles, i_handle, mp_id, scheme, mask):
    print(handles[0][i_handle]['start_time'])
    if mp_id == 30:
        assert handles[0][i_handle]['start_time'] == handles[2][i_handle]['start_time']
        wrfmp = handles[2][i_handle].load()
    else:
        wrfmp = None
    data = handles[0][i_handle].load()
    mp_mean = _get_psd(data, mask, scheme, mp_id, wrfmp)
    return mp_mean


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    mask = np.load(cfg['masks']['Distance'])
    scheme_objs = {8: schemes.MP8(), 10: schemes.MP10(), 28: schemes.MP28(), 30: schemes.MP30(),
                   50: schemes.MP50()}
    psd_mean = {}
    for mp_id, scheme in scheme_objs.items():
        cfg['mp'] = mp_id
        wrfmp_bool = (mp_id == 30)
        handles = models.get_wrf_handles(cfg, wrfmp=wrfmp_bool)
        print(mp_id)
        psd_mean[mp_id] = None
        for i_handle, _ in enumerate(handles[0]):
            mp_mean = _calc_mean_psd(handles, i_handle, mp_id, scheme, mask)
            if psd_mean[mp_id] is None:
                psd_mean[mp_id] = mp_mean
            else:
                psd_mean[mp_id] += mp_mean
        # psd_mean is sum over all timesteps, calculate average by dividing through nr of timesteps
        psd_average = psd_mean[mp_id] / (len(handles[0]) + 1)
        _save(psd_average, mp_id, cfg)


def _get_bins(bin_limits):
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


def _get_psd(data, d_mask, scheme, mp_id, wrfmp=None):
    diameters = schemes.get_diameters()[17:]  # Diameters include cloud and rain, rain start at 17
    # This creates a mask of shape (len(q_thresh), data.shape) which is True when the data is
    # below the threshold --> Data array is repeated len(q_threshs) times along new dimension.
    q_mask = np.greater.outer(Q_THRESHS, data['QRAIN'].values[0][Z_IDX])
    q_mass = _mask_and_repeat(data['QRAIN'].values[0][Z_IDX], q_mask, d_mask)
    q_number = _mask_and_repeat(data['QNRAIN'].values[0][Z_IDX], q_mask, d_mask)
    shape = [len(diameters)] + [len(Q_THRESHS)] + list(data['QRAIN'].values[0][Z_IDX].shape)
    psd = np.empty(shape)
    psd[:] = np.nan
    if mp_id == 30:
        ind = np.index_exp[Z_IDX, :, :]
        for i, thresh in enumerate(Q_THRESHS):
            psd[:-1, i] = scheme.get_psd("rain", wrfmp, ind, thresh)
    else:
        for i, diam in enumerate(diameters):
            psd[i] = scheme.get_psd("rain", diam, q_mass, q_number)

    psd = np.nanmean(psd, axis=(2, 3))
    psd = np.where(np.isnan(psd), 0, psd)  # NaN means empty --> equals 0
    return psd


def _save(psd_mean, mp_id, cfg):
    psd_path = cfg['output']['PSD'] + os.sep + str(cfg['start']) + "_TO_" + str(cfg['end']) + os.sep
    print(psd_path)
    output_mean = utils.make_folder(psd_path) + str(mp_id) + "_mean.npy"
    np.save(output_mean, psd_mean)


if __name__ == "__main__":
    _main(CONFIG_FILE)
