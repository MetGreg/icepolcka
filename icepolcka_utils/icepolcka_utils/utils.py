"""Utility module

Some utility functions. Vector transformations, and other functions that I repeatedly use.

"""
import os
import datetime as dt

import yaml
import numpy as np


class Config:
    """Configuration class

    Used as a container for configurations and to load the configuration data from a configuration
    yaml file.

    Attributes:
        cfg (dict): Configuration dictionary.

    """
    def __init__(self):
        self.cfg = None

    def load_config(self, config_file):
        """Loads the configuration and saves it to object

        Args:
            config_file (str): Path to configuration file.

        """
        cfg_dict = self._open_config_file(config_file)
        self._save_config(cfg_dict)

    def _save_config(self, cfg):
        self.cfg = cfg

    @staticmethod
    def _open_config_file(config_file):
        with open(config_file, encoding="utf-8") as cfg_file:
            cfg = yaml.load(cfg_file, Loader=yaml.SafeLoader)
        # Transform any existing string time entries to datetime for later processing
        try:
            cfg['start'] = dt.datetime.strptime(cfg['start'], "%d.%m.%Y %H:%M:%S")
        except KeyError:
            pass
        try:
            cfg['end'] = dt.datetime.strptime(cfg['end'], "%d.%m.%Y %H:%M:%S")
        except KeyError:
            pass
        try:
            cfg['date'] = dt.datetime.strptime(cfg['date'], "%d.%m.%Y")
        except KeyError:
            pass
        return cfg


def make_folder(output, mp_id=None, radar=None, date=None, hm_name=None):
    """Make output folder

    Given a folder, this function creates subdirectories according to radar, mp-scheme and time.

    Args:
        output (str): Path at which the output folder is created.
        mp_id (int): WRF ID of microphysics scheme.
        radar (str): Name of radar.
        date (~datetime.datetime). Time of data step.
        hm_name (str): Name of hydrometeor class.

    Returns:
        (str):
            Path to output folder.

    """
    if mp_id is not None:
        output = output + os.sep + "MP" + str(mp_id) + os.sep
    if radar is not None:
        output = output + os.sep + radar + os.sep
    if hm_name is not None:
        output = output + os.sep + hm_name + os.sep
    if date is not None:
        output = output + os.sep + str(date.year) + os.sep + f"{date.month:02d}" + os.sep \
                 + f"{date.day:02d}" + os.sep
    try:
        os.makedirs(output)
    except FileExistsError:
        pass
    return os.path.normpath(output) + os.sep


def get_mean_angle(angle1, angle2):
    """Calculate the mean of two angles

    The mean angle is calculated by transforming each angle to x, y Cartesian vector components and
    averaging the components each, before retransforming the vector components back to a
    meteorological angle.

    Args:
        angle1 (~numpy.ndarray or float): First meteorological angle.
        angle2 (~numpy.ndarray or float): Second meteorological angle.

    Returns:
        numpy.ma.core.MaskedArray:
            Mean meteorological angle.

    """
    u_cart1, v_cart1 = _polar_to_xy(1, angle1)
    u_cart2, v_cart2 = _polar_to_xy(1, angle2)
    u_mean, v_mean = (u_cart1 + u_cart2)/2, (v_cart1 + v_cart2)/2
    angle_mean = _vec_to_meteo(u_mean, v_mean)
    return angle_mean


def mask_data(data, mask):
    """Mask data array

    Masks an array with the given mask. True means the value will be put to nan.

    Args:
        data (~numpy.ndarray): Input array.
        mask (~numpy.ndarray): Input mask. Must be same shape as data. True means the value will be
            put to nan.

    Returns:
        ~numpy.ndarray:
            Masked array, where all values are put to nan that correspond to 'True' in the input
            mask.

    """
    # Transform mask and data to float arrays, because filling with np.nan does not work for int
    mask = mask.astype("float64")
    data = data.astype("float64")
    masked = np.ma.masked_array(data, mask, fill_value=np.nan).filled()
    return masked


def get_cfg(cfg_file):
    """Get configuration

    Loads the configuration from a yaml file. If the configured source is "DWD", then the MP-scheme
    will be overwritten with None (because the DWD data has no MP-scheme).

    Args:
        cfg_file (str): Path to configuration file.

    Returns:
        (dict): Configuration loaded into a dictionary.

    """
    config = Config()
    config.load_config(cfg_file)
    cfg = config.cfg

    # Put mp-ID of DWD source data to NaN, because DWD data has not MP-scheme
    try:
        if cfg['source'] == "DWD":
            cfg['mp'] = None
    except KeyError:
        pass
    return cfg


def _polar_to_xy(r_polar, az_polar):
    if np.logical_or(np.any(az_polar < 0), np.any(az_polar > 360)):
        raise ValueError("Azimuth angles must be between 0 and 360")
    math_az = (90 - az_polar + 360) % 360
    u_cart = np.cos(np.radians(math_az))*r_polar
    v_cart = np.sin(np.radians(math_az))*r_polar
    return u_cart, v_cart


def _vec_to_meteo(u_vec, v_vec):
    u_vec = np.asarray(u_vec)
    v_vec = np.asarray(v_vec)
    mask = np.logical_and(u_vec == 0, v_vec == 0)  # Vectors (0, 0) not valid.
    met_ang = np.ma.masked_array((90 - np.degrees(np.arctan2(v_vec, u_vec)) + 360) % 360, mask=mask,
                                 fill_value=np.nan)
    return met_ang
