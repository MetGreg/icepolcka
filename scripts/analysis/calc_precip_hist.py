"""Plot precipitation histograms

Plots a simple histogram for the precipitation as simulated by WRF directly for
several different microphysics schemes.

"""
import json
import os
import datetime as dt
import numpy as np

from icepolcka_utils.data_base import WRFDataBase
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


def get_handles(wrf_data, date, mp):
    """Get WRF data

    Gets the wrf data handles from the WRFDataBase corresponding to
    the data within the time range, and microphysics that was configured.

    Args:
        date (datetime.datetime): Date of interest.
        wrf_data (WRFDataBase): Opened WRF data base.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List of all data handles corresponding to configured input.

    """
    start = dt.datetime(date.year, date.month, date.day, 0, 0, 0)
    end = dt.datetime(date.year, date.month, date.day, 23, 59, 59)
    handles = wrf_data.get_data(start, end, mp_id=mp, domain="Munich")
    return handles


def calc_precip(handle, mask):
    """Calculate total precipitation

    For the given data handle, this function sums up precipitation over all
    surface grid boxes within Mira-35 range. A mask is applied to consider only
    the Mira-35 range. The total precipitation in one grid box is the sum of
    the grid scale and subgrid scale precipitation. The WRF output is given
    in units of mm. That means, the total volume of water in one grid box in
    SI-units (m³) is:
    precip / 1000 (m) * area (m²),
    where precip is the sum of grid and subgrid precipitation, the factor of
    1/1000 is due to the transformation of mm to m and the grid box area is
    400**2 in the case of our icepolcka domain. For all surface grid boxes:
    precip1 / 1000  * area + precip2 / 1000 * area ....
    = sum(precip) / 1000  * area

    Args:
        handle (dict): Dictionary containing WRF data handles.
        mask (numpy.ndarray): Distance mask to mask grid boxes outside of
            Mira-35 range. True, if within Mira-35 range. Must be of the same
            shape as the WRF surface grid.

    Returns:
        float:
            Total precipitation [m³] summed over the Mira-35 domain.

    """
    data = handle['wrfout'].load()
    grid_precip = np.nansum(np.where(mask, data['PREC_ACC_NC'].values[0],
                                     np.nan))
    subgrid_precip = np.nansum(np.where(mask, data['PREC_ACC_C'].values[0],
                                        np.nan))
    total_precip = (grid_precip + subgrid_precip)*400**2/1000
    return total_precip


def save_hist(total_precip, date, output):
    """Save precipitation sum to netcdf


    """
    date_str = dt.datetime.strftime(date, "%d%m%Y")
    output_file = make_folder(output + os.sep + "data") + date_str + ".json"
    with open(output_file, "w") as f:
        json.dump(total_precip, f)


def main():
    print("Starting main")
    cfg = load_config()
    mask = np.load(cfg['masks']['Distance'])
    total_precip = init_dict(MPS)
    with WRFDataBase(cfg['data']['WRF'], cfg['database']['WRF'],
                     update=cfg['update'], recheck=cfg['recheck']) as wrf_data:
        for mp in MPS:
            print("MP: ", str(mp))
            handles = get_handles(wrf_data, cfg['date'], mp)
            for handle in handles:
                if "wrfout" not in handle.keys():
                    continue
                else:
                    precip = calc_precip(handle, mask)
                    total_precip[mp] += precip
    save_hist(total_precip, cfg['date'], cfg['output']['PRECIP'])


if __name__ == "__main__":
    main()
