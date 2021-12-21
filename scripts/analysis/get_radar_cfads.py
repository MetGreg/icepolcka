"""This script creates some visualizations to compare model and radar"""
import os
import datetime as dt
import numpy as np
import pandas as pd
import wradlib as wrl
from osgeo import osr

from icepolcka_utils.data_base import MiraDataBase, PoldiDataBase
from icepolcka_utils.geo import get_pos_from_dist
from icepolcka_utils.grid import create_column
from icepolcka_utils.projection import spherical_to_cart, data_to_cart
from icepolcka_utils.utils import load_config


# Settings not defined by the configuration file
MAX_DT = 300  # Max allowed time diff between poldi and mira scan in sec

# These are the dates where we did coordinated measurements
DATES = ["28.05.2019", "21.06.2019", "01.07.2019", "07.07.2019", "08.07.2019"]


def prepare_dicts(variables, heights):
    """Prepare dictionary containers

    Prepares two dictionaries, one for Mira-35, one for Poldirad. The
    dictionaries have entries for each variable. The corresponding dictionary
    values are lists that have the same length as the heights array and are
    filled with None.

    These dictionaries will later be filled with histograms, one for each
    height. This is then the CFAD array.

    Args:
        variables (list): List of variable names.
        heights (list or numpy.ndarray): List of height steps [m].

    Returns:
        (dict, dict):
            1) Container for Poldirad CFADs.
            2) Container for Mira-35 CFADs.

    """
    poldi_stacked = {}
    mira_stacked = {}
    for var in variables:
        poldi_stacked[var] = [None for i in range(len(heights))]
        mira_stacked[var] = [None for i in range(len(heights))]
    return poldi_stacked, mira_stacked


def read_logs(date, log):
    """Read log book

    Opens the log book corresponding to the date and returns all scans as a
    pandas data frame.

    Args:
        date (str): Date of logbook (%d.%m.%Y)
        log (str): Path to log book.

    Returns:
        pandas.core.frame.DataFrame:
            Dataframe containing the scans read from the log book.

    """
    date = dt.datetime.strptime(date, "%d.%m.%Y")
    date_str = dt.datetime.strftime(date, "%Y%m%d")
    with open(log + date_str + ".csv") as text:
        scans = pd.read_csv(text, delimiter=",", encoding="ISO-8859-1")
    return scans


def get_time(scans, index):
    """Get start and end time of current Sector RHI

    Finds the time of the current scan and the next scan. If there is no next
    scan, the end time is the current time plus 5 minutes.

    Args:
        scans (pandas.core.frame.DataFrame): Dataframe containing all scans.
        index (int): Index of current scan.

    Returns:
        (datetime.datetime, datetime.datetime):
            1) Start time of current scan [UTC]
            2) Start time of next scan [UTC]

    """
    scan = scans.iloc[index]
    scan_date = int(scan['Date'])
    time = int(scan['Time'])
    start_time = dt.datetime.strptime(str(scan_date) + str(time),
                                      "%Y%m%d%H%M%S")
    if index == len(scans) - 1:
        end_time = start_time + dt.timedelta(seconds=300)
    else:
        next_scan = scans.iloc[index + 1]
        end_date = int(next_scan['Date'])
        end_time = int(next_scan['Time'])
        end_time = dt.datetime.strptime(str(end_date) + str(end_time),
                                        "%Y%m%d%H%M%S")
    return start_time, end_time


def time_diff(poldi_handle, mira_handle, start_time):
    """Check time difference

    Check, if Poldirad and Mira-35 data are apart more than a predefined
    number of seconds. If they are, return True.

    Args:
        poldi_handle (ResultHandle): Poldirad data handle.
        mira_handle (ResultHandle): Mira-35 data handle.
        start_time (datetime.datetime): Time [UTC] of current log book entry.

    Returns:
        bool:
            True, if scans are more than MAX_DT seconds apart.

    """
    # Print warning if scan times are too much apart
    diff = abs(mira_handle['start_time'] - poldi_handle['start_time'])
    if diff > dt.timedelta(seconds=MAX_DT):
        print("time_diff too big: ", start_time)
        return True


def get_poldi_coords(poldi_handle, mira_handle, matrix):
    """Get Poldirad coordinates

    Given a Poldirad and Mira-35 scan, this function returns the azimuth and
    distance [m] from Poldirad where the Mira-35 and Poldirad beams
    intersect. This information is loaded from a precalculated matrix.

    Args:
        poldi_handle (ResultHandle): Poldirad data handle.
        mira_handle (ResultHandle): Mira-35 data handle.
        matrix (numpy.ndarray): Table that defines the distance [m] to
            Poldirad and Mira-35 where beams would intersect, for a number of
            azimuth angles. Outer dimension: Poldirad azimuth angles (0 to 140),
            inner dimension: Mira-35 azimuth angles (0 to 360). For each
            combination, a tuple of (Poldirad, Mira-35) distance is expected.

    Returns:
        (int, int or None):
            1) Polidrad azimuth angle towards beam intersection.
            2) Poldirad range [m] towards beam intersection.

    """
    mira_az = int(np.round(mira_handle['azimuth'])) % 360
    poldi_az = int(np.round(poldi_handle['azimuth']))
    poldi_r, mira_r = matrix[poldi_az, mira_az]
    return poldi_az, poldi_r


def check_error(poldi_handle, mira_handle, start_time, matrix):
    """Check for errors

    This function checks if there are any errors. This can happen if the
    Poldirad and Mira-35 scans are too far apart, or if the given Poldirad and
    Mira-35 scans do not intersect. If an error is found, the function
    returns True.

    poldi_handle (ResultHandle): Poldirad data handle.
    mira_handle (ResultHandle): Mira-35 data handle.
    start_time (datetime.datetime): Time [UTC] of current scan.
    matrix (numpy.ndarray): Table that defines the distance [m] to
        Poldirad and Mira-35 where beams would intersect, for a number of
        azimuth angles. Outer dimension: Poldirad azimuth angles (0 to 140),
        inner dimension: Mira-35 azimuth angles (0 to 360). For each
        combination, a tuple of (Poldirad, Mira-35) distance is expected.

    Returns:
        bool:
            True, if any error was found.

    """
    if time_diff(poldi_handle, mira_handle, start_time):
        return True
    poldi_az, poldi_r = get_poldi_coords(poldi_handle, mira_handle, matrix)
    if poldi_r is None:
        return True


def get_src_coords(scan, mask=None):
    """Get source coordinates

    Given a scan object, this function calculates the Cartesian source
    coordinates from the range, azimuth and elevation input coordinates.

    Args:
        scan (xarray.core.dataset.Dataset): Xarray containing the scan
            coordinates.
        mask (numpy.ndarray): If mask array is given, the corresponding
            entries will be removed. This makes sense to remove NaNs to reduce
            the number of source points.

    Returns:
        (numpy.ndarray_, SpatialReference_): Array of source coordinates,
            Corresponding projection object.

    """
    if mask is not None:
        elv = scan.elv.values[scan.elv.notnull().values]
        az = scan.az.values[scan.az.notnull().values]
    else:
        elv, az = scan.elv, scan.az
    # Azimuth and Elevation have same shape, but r has not
    r, az = np.meshgrid(scan.r, az)
    r, elv = np.meshgrid(scan.r, elv)
    src, proj_rad = spherical_to_cart(r.ravel(), az.ravel(), elv.ravel(),
                                      scan.site_coords)
    return src, proj_rad


def get_target_cart(target_coords, proj_poldi):
    """Get target grid

    Creates the 1D target grid profile above the given lon/lat coordinates.

    Args:
        target_coords (tuple): Lon/lat coordinates of target point.
        proj_poldi (SpatialReference_): Projection of target grid.

    Returns:
        numpy.ndarray_:
            Array of target Cartesian Profile.

    """
    # Get target coordinates in Cartesian coordinates
    proj_geo = osr.SpatialReference()
    proj_geo.ImportFromEPSG(4326)
    target_cart = wrl.georef.reproject(target_coords,
                                       projection_source=proj_geo,
                                       projection_target=proj_poldi)
    return target_cart


def get_var_key(var):
    """Get variable key

    When the Dual-wavelength "DWR" CFAD is created, the actual data key
    is "reflectivity". This function returns the data key that corresponds to
    the current variable.

    Args:
        var (str): Variable name.

    Returns:
        str:
            Data key corresponding to variable name.

    """
    if var in ["DWR", "Zhh"]:
        var_data = "reflectivity"
    elif var == "Zdr":
        var_data = "zdr"
    elif var == "Kdp":
        var_data = "kdp"
    else:
        var_data = var
    return var_data


def calc_hist(bin_limits, var, heights, poldi_int, mira_int, poldi_stacked,
              mira_stacked):
    """Calculate histograms

    For each height, calculates a histogram according to the given bins and
    data for the given variable for each, Poldirad and Mira.

    Args:
        bin_limits (dict): Dictionary with min, max and steps of bins for each
            variable.
        var (str): Variable name.
        heights (numpy.ndarray_): Height steps.
        poldi_int (numpy.ndarray_): Poldirad data interpolated to target 1D
            profile.
        mira_int (numpy.ndarray_): Mira data interpolated to target 1D profile.
        poldi_stacked (dict): Poldirad container for the histogram to be added
            for the given variable.
        mira_stacked (dict): Mira container for the histogram to be added for
            the given variable.

    Returns:
        (dict, dict):
            Tuple of dictionary for (Poldirad, Mira) data with the new
            variable included. The dictionaries contain each variable as a key.
            The values are lists with histograms for each height step.

    """
    xmin = bin_limits[var][0]
    xmax = bin_limits[var][1]
    steps = bin_limits[var][2]
    bins = np.arange(xmin, xmax + steps, steps)
    for i in range(len(heights)):
        poldi_hist = np.histogram(poldi_int[i], bins=bins)[0]
        if var not in ["zdr", "kdp"]:
            mira_hist = np.histogram(mira_int[i], bins=bins)[0]
        if poldi_stacked[var][i] is None:
            poldi_stacked[var][i] = poldi_hist
            if var not in ["zdr", "kdp"]:
                mira_stacked[var][i] = mira_hist
        else:
            poldi_stacked[var][i] += poldi_hist
            if var not in ["zdr", "kdp"]:
                mira_stacked[var][i] += mira_hist
    return poldi_stacked, mira_stacked


def get_cfads(variables, heights, dates, poldi_db, mira_db, matrix, bins, log):
    """Get CFAD array

    This function returns two dictionaries, one for Mira-35 and one for
    Poldirad. For each variable, the dictionaries contain a numpy array that
    consists, for each height step, of a histogram the variable values over a
    number of bins.

    The function loops through all dates, scans and cells, finds the
    radar data that corresponds to the time step. The intersection of the
    radar beams at the given azimuth angles is loaded from the precalculated
    matrix array. At this intersection point, a 1D profile is defined with a
    100 m resolution. The radar data is then interpolated to this profile
    with a Nearest Neighbor interpolation.

    Also, only time steps within the given PERIODS and cells within the Mira-35
    range are considered.

    Args:
        variables (list): Variable names.
        heights (list or numpy.ndarray): Height steps of the CFAD [m].
        dates (list): List of dates of interest.
        poldi_db (PoldiDataBase): Opened Poldirad data base.
        mira_db (MiraDataBase): Opened Mira-35 data base.
        matrix (numpy.ndarray): Table that defines the distance [m] to
            Poldirad and Mira-35 where beams would intersect, for a number of
            azimuth angles. Outer dimension: Poldirad azimuth angles (0 to 140),
            inner dimension: Mira-35 azimuth angles (0 to 360). For each
            combination, a tuple of (Poldirad, Mira-35) distance is expected.
        bins (dict): Minimum, maximum and resolution of the variable bins.
        log (str): Path to log book file.

    Returns:
        (dict, dict):
            1) Poldirad CFADs. For each variable, an array of histograms at
                each height step.
            2) Mira-35 CFADs. For each variable, an array of histograms at
                each height step.

    """
    mira_stacked, poldi_stacked = prepare_dicts(variables, heights)
    i, j = 0, 0  # Counter for number of scans included
    for date in dates:
        scans = read_logs(date, log)
        for index, scan in scans.iterrows():
            start_time, end_time = get_time(scans, int(index))
            print(start_time)
            poldi_handles = poldi_db.get_closest_srhi(start_time)
            mira_handles = mira_db.get_rhis(start_time, end_time)

            for poldi_handle in poldi_handles:
                for mira_handle in mira_handles:
                    i += 1
                    if check_error(poldi_handle, mira_handle, start_time,
                                   matrix):
                        continue
                    j += 1
                    poldi_rhi = poldi_handle.load()
                    mira_rhi = mira_handle.load()
                    mask = poldi_rhi.times.notnull().values

                    # Get source coordinates
                    poldi_src, proj_poldi = get_src_coords(poldi_rhi, mask)
                    mira_src, proj_mira = get_src_coords(mira_rhi)

                    # Transform mira coords to poldirad source grid
                    mira_src = wrl.georef.reproject(
                        mira_src, projection_source=proj_mira,
                        projection_target=proj_poldi
                        )

                    poldi_az, poldi_r = get_poldi_coords(poldi_handle,
                                                         mira_handle, matrix)
                    target_coords = get_pos_from_dist(poldi_rhi.site_coords,
                                                      poldi_r, poldi_az)
                    target_cart = get_target_cart(target_coords, proj_poldi)

                    # Create the target grid
                    trg_grid = create_column(target_cart, heights)

                    itp_mira, itp_poldi = None, None
                    for var in variables:
                        var_key = get_var_key(var)

                        # Interpolate data to 3D grid
                        if var == "Zdr":
                            poldi_rhi['zdr'].values -= 0.15
                        poldi_data = poldi_rhi[var_key].values[mask]
                        poldi_int, itp_poldi = data_to_cart(
                            poldi_data.ravel(), poldi_src, trg_grid,
                            itp=itp_poldi
                            )
                        if var_key not in ["zdr", "kdp"]:
                            mira_int, itp_mira = data_to_cart(
                                mira_rhi[var_key].values.ravel(),
                                mira_src, trg_grid, itp=itp_mira
                                )
                        if var == "DWR":
                            poldi_int = poldi_int - mira_int
                            mira_int = poldi_int

                        poldi_stacked, mira_stacked = calc_hist(
                            bins, var, heights, poldi_int,
                            mira_int, poldi_stacked, mira_stacked
                            )
    print('NUMBER OF SCANS')
    print(i)
    print('USEFUL SCANS')
    print(j)
    return poldi_stacked, mira_stacked


def make_folders(output):
    """Make output folder

    Make output folder for each radar.

    Args:
        output (str): Path at which the output sub folders are created.

    """
    radars = ["Mira35", "Poldirad"]
    for radar in radars:
        cfad_output = output + os.sep + radar + os.sep
        if not os.path.exists(cfad_output):
            os.makedirs(cfad_output)


def save(output, variables, poldi, mira):
    """Save CFADs

    Save CFAD arrays to numpy array.

    Args:
        output (str): Path to CFAD folder.
        variables (list): List of variable names.
        poldi (dict): Poldirad CFADs. For each variable, an array of histograms
            at each height step.
        mira (dict): Mira-35 CFADs. For each variable, an array of histograms at
            each height step.

    """
    output = output + os.sep + "radar" + os.sep
    poldi_output = output + "Poldirad" + os.sep
    mira_output = output + "Mira35" + os.sep
    make_folders(output)
    for var in variables:
        np.save(poldi_output + var, np.array(poldi[var]))
        if var not in ["zdr", "kdp"]:
            np.save(mira_output + var, np.array(mira[var]))


def main(cfg_file):
    cfg = load_config(cfg_file)
    matrix = np.load(cfg['matrix']['Intersection'], allow_pickle=True)
    variables = ["Zhh", "Zdr", "DWR", "Kdp"]
    heights = np.array(cfg['WRFGrid'])*1000  # WRFGrid config in [km]

    with MiraDataBase(cfg['data']['MIRA'], cfg['database']['MIRA'],
                      recheck=cfg['recheck'], update=cfg['update']) as mira_db:
        with PoldiDataBase(cfg['data']['POLDI'], cfg['database']['POLDI'],
                           recheck=cfg['recheck'],
                           update=cfg['update']) as poldi_db:

            poldi, mira = get_cfads(variables, heights, DATES, poldi_db,
                                    mira_db, matrix, cfg['bins'],
                                    cfg['logbooks']['Coordinated_RHI'])

    save(cfg['output']['CFADs'], variables, poldi, mira)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
