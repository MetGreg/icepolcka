"""Utility module

Some utility functions. Vector transformations, and other functions that I
repeatedly use.

"""
import os
import yaml
import datetime as dt
import numpy as np
import numpy.ma as ma


def load_config(config_file):
    """Load configuration

    Loads the configuration from a configuration file.

    Dates and times within the configuration file are transformed do datetime
    objects by this function.

    For an explanation on how to use the configuration file, see the
    repository README file.

    Args:
        config_file (str): Path to configuration file.

    Returns:
        dict:
            Configuration loaded into a dictionary.

    """
    with open(config_file) as cfg_file:
        cfg = yaml.load(cfg_file, Loader=yaml.SafeLoader)

    cfg['start'] = dt.datetime.strptime(cfg['start'], "%d.%m.%Y %H:%M:%S")
    cfg['end'] = dt.datetime.strptime(cfg['end'], "%d.%m.%Y %H:%M:%S")
    cfg['date'] = dt.datetime.strptime(cfg['date'], "%d.%m.%Y")
    return cfg


def make_folder(output, mp=None, radar=None, date=None, hm=None):
    """Make output folder

    Given a folder, this function creates subdirectories according to radar,
    mp-scheme and time.

    Args:
        output (str): Path at which the output folder is created.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Name of radar.
        date (datetime.datetime). Time of data step.
        hm (str): Name of hydrometeor class.

    Returns:
        str:
            Path to output folder.

    """
    if mp is not None:
        output = output + os.sep + "MP" + str(mp) + os.sep
    if radar is not None:
        output = output + os.sep + radar + os.sep
    if hm is not None:
        output = output + hm + os.sep
    if date is not None:
        output = output + str(date.year) + os.sep + f"{date.month:02d}" \
            + os.sep + f"{date.day:02d}" + os.sep
    try:
        os.makedirs(output)
    except FileExistsError:
        pass
    return output + os.sep


def vec_to_meteo(u, v):
    """Get meteorological angle of input vector.

    Args:
        u (numpy.ndarray or float): U-components of input vectors.
        v (numpy.ndarray or float): V-components of input vectors.

    Returns:
        numpy.MaskedArray:
            Meteorological angles (North=0, South=180).

    """
    u = np.asarray(u)
    v = np.asarray(v)
    mask = np.logical_and(u == 0, v == 0)  # Vectors (0, 0) not valid.
    met_ang = ma.masked_array((90 - np.degrees(np.arctan2(v, u)) + 360) % 360,
                              mask=mask, fill_value=np.nan)
    return met_ang


def meteo_to_math(met_angle):
    """Convert meteorological to mathematical angles.

    Args:
        met_angle (numpy.ndarray or float): Meteorological angles.

    Returns:
        numpy.ndarray or float:
            Mathematical angles.

    """
    if np.logical_or(np.any(met_angle > 360),  np.any(met_angle < 0)):
        raise ValueError("Meteorological angles must be between 0 and 360")
    math_angle = (90 - met_angle + 360) % 360
    return math_angle


def polar_to_xy(r, az):
    """Transform polar coordinates to Cartesian x, y coordinates

    Transforms azimuth angle to mathematical angles and uses trigonometric
    functions to obtain Cartesian x, y - values out of angle and radius.

    Args:
        r (numpy.ndarray or float): Array of ranges [m].
        az (numpy.ndarray or float): Corresponding array of azimuths angles.

    Returns:
        numpy.ndarray or float:
            Array of Cartesian x, y coordinates.

    """
    if np.logical_or(np.any(az < 0), np.any(az > 360)):
        raise ValueError("Azimuth angles must be between 0 and 360")
    if np.any(r < 0):
        raise ValueError("Range values must be greater than 0")
    math_az = meteo_to_math(az)  # Transform meteo. to mathematical angles.
    u = np.cos(np.radians(math_az))*r
    v = np.sin(np.radians(math_az))*r
    return u, v


def get_mean_angle(angle1, angle2):
    """Calculate the mean of two angles

    The mean angle is calculated by transforming each angle to x, y Cartesian
    vector components and averaging the components each, before retransforming
    the vector components back to an meteorological angle.

    Args:
        angle1 (numpy.ndarray or float): First meteorological angle.
        angle2 (numpy.ndarray or float): Second meteorological angle.

    Returns:
        numpy.MaskedArray:
            Mean meteorological angle.

    """
    u1, v1 = polar_to_xy(1, angle1)
    u2, v2 = polar_to_xy(1, angle2)
    u_mean, v_mean = (u1 + u2)/2, (v1 + v2)/2
    angle_mean = vec_to_meteo(u_mean, v_mean)
    return angle_mean
