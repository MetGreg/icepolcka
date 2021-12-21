"""Calculate PSD CFADs

Creates Contoured Frequency by Altitude Distribution (CFADs) for Particle
Size distributions (PSD). This script does not plot anything, but instead
calculates the frequency distribution and saves this to a numpy array. The
height steps are predefined using height levels from a specific WRF simulation.
A histogram of the Particle size distribution for each of these height steps is
calculated and stacked to one big numpy array that is saved. The date range, mp
scheme and other settings are defined using the configuration file.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import wrf
import datetime as dt
import numpy as np
from netCDF4 import Dataset

from icepolcka_utils.data_base import WRFDataBase, CRSIMDataBase, TracksDataBase
from icepolcka_utils.geo import get_target_distance
from icepolcka_utils.schemes import MP8, MP10, MP28, MP30, MP50
from icepolcka_utils.utils import load_config, make_folder


PERIODS = [
    [dt.datetime(2019, 5, 28, 11, 20), dt.datetime(2019, 5, 28, 14, 5)],
    [dt.datetime(2019, 6, 21, 14, 40), dt.datetime(2019, 6, 21, 17, 25)],
    [dt.datetime(2019, 7, 1, 11, 20), dt.datetime(2019, 7, 1, 16, 50)],
    [dt.datetime(2019, 7, 7, 9, 20), dt.datetime(2019, 7, 7, 15, 10)],
    [dt.datetime(2019, 7, 8, 9), dt.datetime(2019, 7, 8, 14)]
    ]


def get_tracks(path, db, update, recheck, start, end, mp):
    """Get tracks data

    Gets the tracks handles from the TracksDataBase corresponding to
    the data within the time range, and microphysics that was configured.

    Args:
        path (str): Path to Tracks data.
        db (str): Path to Tracks data base file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List of all data handles corresponding to configured input.

    """
    print("Getting Tracks")
    with TracksDataBase(path, db, update=update,
                        recheck=recheck) as tracks_data:
        tracks = tracks_data.get_data(start, end, source="MODEL", mp_id=mp,
                                      radar="Isen")
    return tracks


def load_tracks(track):
    """Load tracks data

    Loading the tracks data and transforming it to a pandas data frame.

    Args:
        track (ResultHandle): Handle that contains track data.

    Returns:
        pandas.core.frame.DataFrame:
            Loaded tracks data.

    """
    tracks_data = track.load()
    tracks_df = tracks_data.to_dataframe()
    tracks_df = tracks_df.dropna()
    return tracks_df


def get_wrf_data(wrf_db, time, mp):
    """Get WRF data

    Given a time and a MP scheme ID, this function returns the loaded WRF data
    sets.

    Args:
        wrf_db (WRFDataBase): Opened WRF data base.
        time (datetime.datetime): Time step [UTC] at which the closest
            WRF data will be returned.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        (xarray.core.dataset.Dataset, xarray.core.dataset.Dataset):
            1) Loaded dataset of WRF data in xarray
            2) Loaded dataset of WRF data in ncdf4 Dataset
            3) Resulthandle

    """
    handle = wrf_db.get_closest_data(time, mp_id=mp)
    if handle['clouds']['start_time'] - time > dt.timedelta(seconds=300):
        print("No WRF data found for time step: ", time)
        exit()
    data = handle['clouds'].load()
    ds = Dataset(handle['clouds']['file_path'])
    return data, ds, handle


def get_crsim_data(crsim_db, time, mp):
    """Get CR-SIM data

    Given a time and a MP scheme ID, this function returns the loaded CR-SIM
    data sets.

    Args:
        crsim_db (CRSIMDataBase): Opened CR-SIM data base.
        time (datetime.datetime): Time step [UTC] at which the closest
            CR-SIM data will be returned.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        (xarray.core.dataset.Dataset, xarray.core.dataset.Dataset):
            1) Loaded dataset of CR-SIM data in xarray

    """
    handle = crsim_db.get_closest_data(time, mp_id=mp)
    if handle['time'] - time > dt.timedelta(seconds=300):
        print("No CR-SIM data found for time step: ", time)
        exit()
    data = handle.load()
    return data


def mask_data(data, cell_mask):
    """Mask data

    Applies two masks onto the data. One for the cell location, that masks
    all grid boxes not within the cell. The other one masks everything that
    is not within the highest and lowest radar beam.

    Args:
        data (xarray.core.dataArray.DataArray): Data that will be masked.
        cell_mask (numpy.ndarray): Mask for the convective cell. True,
            if grid box is within convective cell.

    Returns:
        numpy.ndarray:
            Masked data. Everything that is masked is put to numpy.nan

    """
    masked_data = np.where(cell_mask, data.values, np.nan)
    return masked_data


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


def stack_histograms(cfad_stacked, data, heights, heights_grid, bins):
    """Stack histogram container with new data

    The CFAD container are dictionaries with one key for each variable. The
    corresponding value is the CFAD for this variable: A numpy array with a
    histogram for each height. This function loops through all heights,
    calculates the histogram and adds it to the CFAD container. This is done
    for both radars, Mira-35 and Poldirad.

    Args:
        cfad_stacked (list): Container for CFAD. A list/array of the same
            length as heights.
        data (numpy.ndarray): 3D data array of WRF.
        heights (numpy.ndarray): Height steps of the CFADs.
        heights_grid (numpy.ndarray): Height steps of the WRF Grid input
            data.
        bins (numpy.ndarray): Bins that will be used for the histograms.

    Returns:
        (list):
            1) CFAD container, filled with the histograms.

    """
    for i in range(len(heights)):
        h = heights[i]
        h_grid = np.where(np.isclose(heights_grid, h))[0][0]
        hist = np.nansum(np.nansum(data[:, h_grid, :, :], axis=-1), axis=-1)

        #hist = np.histogram(data[h_grid], bins=bins)[0]
        if cfad_stacked[i] is None:
            cfad_stacked[i] = hist
        else:
            cfad_stacked[i] += hist
    return cfad_stacked


def get_psd(data, ds, diameters, scheme, mask, mp, wrfmp=None):
    """Calculate the PSD

    Args:
        data ():
        ds ():
        diameters ():
        scheme ():
        mask ():

    Returns:
        (numpy.ndarray):
            Array of

    """
    shape = [len(diameters)] + list(data['QRAIN'].values[0].shape)
    psd = np.empty(shape)
    psd[:] = np.nan
    p = wrf.getvar(ds, "pressure")*100
    t = wrf.getvar(ds, "tk")
    box_counter = 0

    for z in range(len(p)):
        for y in range(len(p[z])):
            for x in range(len(p[z, y])):
                if not mask[y, x]:
                    continue
                qr = data['QRAIN'].values[0, z, y, x]
                qn = data['QNRAIN'].values[0, z, y, x]
                qv = data['QVAPOR'].values[0, z, y, x]
                if qr == 0 or qn == 0 or qv == 0:
                    continue
                box_counter += 1

                if mp == 30:
                    psd[:, z, y, x] = scheme.get_psd("rain", wrfmp, z, y, x)
                else:
                    for d in range(len(diameters)):
                        diam = diameters[d]
                        if mp == 10 or mp == 50:
                            psd[d, z, y, x] = scheme.get_psd("rain", diam, qn,
                                                             qr)
                        elif mp == 8 or mp == 28:
                            psd[d, z, y, x] = scheme.get_psd("rain", diam, qr, qn,
                                                             qv, p[z, y, x],
                                                             t[z, y, x])
    print("Box counter: ", box_counter)
    return psd


def get_diameters():
    """Get diameter bins

    Calculates the bins according to the spectral bin scheme  that uses
    mass-doubling bins. For rain, they start at d=0.2mm and go up to 3.3 mm.

    """
    m = 1000*4/3*np.pi*(2*10**(-6))**3  # Mass of 2µm water droplet
    bins = []
    rho = 1000
    for i in range(33):
        bins.append(((3*m)/(4*rho*np.pi))**(1/3) * 2)
        m = 2*m
    return np.array(bins[17:])


def get_cfads(track, wrf_db, crsim_db, heights, sites, max_range, mp,
              bin_limits, schemes):
    """Get CFAD array

    This function returns two dictionaries, one for Mira-35 and one for
    Poldirad. For each variable, the dictionaries contain a numpy array that
    consists, for each height step, of a histogram the variable values over a
    number of bins.

    The function loads the tracks for the day, loops through all scans and
    cells, finds the RegularGrid data that corresponds to the time step.
    Then, the Regular Grid data is masked so that only the grid boxes within
    the cell are considered and only grid boxes within the highest and lowest
    radar beam.

    Also, only time steps within the given PERIODS and cells within the Mira-35
    range are considered.

    Args:
        track (): CellTracks ResultHandle.
        wrf_db (WRFDataBase): Data base of WRF data.
        crsim_db (WRFDataBase): Data base of crsim data.
        heights (list or numpy.ndarray): Height steps of the CFAD [m].
        sites (dict): Site coordinates (lon/lat/alt) of the radars.
        max_range (int): Maximum range of domain to consider [m].
        mp (int): WRF ID of microphysics scheme.
        bin_limits (dict): Minimum, maximum and resolution of the variable bins.
        schemes (dict): Dictionary containing the MP scheme classes.

    Returns:
        (list):
            1) CFADs: An array of histograms at each height step.

    """
    diameters = get_diameters()
    scheme = schemes[mp]
    cfad_stacked = [None for i in range(len(heights))]

    print(track['date'])
    tracks_df = load_tracks(track)

    # Loop through all cells
    for scan, scan_df in tracks_df.groupby(level=0):
        t_scan = dt.datetime.now()
        # Check if time is within periods of interest
        scan_time = dt.datetime.strptime(str(scan_df['time'].values[0]),
                                            "%Y-%m-%dT%H:%M:%S.%f000")
        if not np.any([p[0] <= scan_time <= p[1] for p in PERIODS]):
            continue

        # Loop through all cells
        print(scan_time)
        new_scan = True
        for cell, cell_df in scan_df.iterrows():
            print(cell)
            t_cell = dt.datetime.now()
            # Check if cell is within mira range
            mira_d = get_target_distance(sites['Mira35'], (cell_df['lon'],
                                                            cell_df['lat']))
            if mira_d > max_range:
                continue

            # If new scan, get corresponding rg data
            if new_scan:
                data, ds, handle = get_wrf_data(wrf_db, scan_time, mp)
                crsim_data = get_crsim_data(crsim_db, scan_time, mp)
                if mp == 30:
                    wrfmp = handle['wrfmp'].load()
                else:
                    wrfmp = None

            # Mask everything that's not a convective cell
            cell_mask = cell_df['mask'].T  # CR-SIM grid transposed to WRF

            h_grid = np.swapaxes(crsim_data.height.values, 1, 2)

            # Calculate PSD
            t_psd = dt.datetime.now()
            psd = get_psd(data, ds, diameters, scheme, cell_mask, mp,
                            wrfmp)
            print('PSD took: ', dt.datetime.now() - t_psd)

            # Calculate histograms at each height
            bins = get_bins(bin_limits['PSD'])
            cfad_stacked = stack_histograms(cfad_stacked, psd, heights,
                                            h_grid, bins)
            new_scan = False
            print('Cell took: ', dt.datetime.now() - t_cell)
        print('Scan took: ', dt.datetime.now() - t_scan)

    return cfad_stacked


def save(output, mp, cfad, track):
    """Save CFADs

    Save CFAD arrays to numpy array.

    Args:
        output (str): Path to CFAD folder.
        mp (int): WRF ID of microphysics scheme.
        cfad (list): CFAD: An array of histograms at each height step.

    """
    output = output + os.sep + "model" + os.sep
    cfad_output = make_folder(output, mp, "PSD") + "PSD_" + str(track['date']) +  ".npy"
    print(cfad_output)
    np.save(cfad_output, np.array(cfad))


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    schemes = {8: MP8(), 10: MP10(), 28: MP28(), 30: MP30(), 50: MP50()}
    heights = np.array(cfg['WRFGrid'])*1000  # WRFGrid config in [km]
    tracks = get_tracks(cfg['data']['TRACKS'], cfg['database']['TRACKS'],
                        cfg['update'], cfg['recheck'], cfg['start'], cfg['end'],
                        cfg['mp'])
    with WRFDataBase(cfg['data']['WRF'], cfg['database']['WRF'],
                     update=cfg['update'], recheck=cfg['recheck']) as wrf_db:
        with CRSIMDataBase(cfg['data']['CRSIM'], cfg['database']['CRSIM'],
                           update=cfg['update'], recheck=cfg['recheck']) \
                as crsim_db:
            for track in tracks:
                cfad = get_cfads(track, wrf_db, crsim_db, heights, cfg['sites'],
                                cfg['max_r'], cfg['mp'], cfg['bins'], schemes)
                save(cfg['output']['CFADs'], cfg['mp'], cfad, track)


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
