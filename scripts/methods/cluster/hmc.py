"""Hydrometeor classification

Applies hydrometeor classification on the regular grid data. Two different hydrometeor
classification algorithms are applied. One is a prototype from Velibor Pejcic, at the time of
writing not yet published. The second one is from Dolan:

Dolan, Brenda, et al. "A robust C-band hydrometeor identification algorithm and application to a
long-term polarimetric radar dataset." Journal of Applied Meteorology and Climatology 52.9 (2013):
2162-2186.

"""
import os
import sys
import datetime as dt

import numpy as np
import xarray as xr

from csu_radartools import csu_fhc

from icepolcka_utils import cluster, utils
from icepolcka_utils.database import handles

DOLAN_LIMS = {'dz': (-27.3, 76.6), 'dr': (-1.8, 6.3), 'kd': (-2.9, 11), 'rh': (0.49, 1.07)}
DOLAN_KEYS = {1: "Drizzle", 2: "Rain", 3: "Ice Crystals", 4: "Aggregates", 5: "Wet Snow",
              6: "Vertical Ice", 7: "LD Graupel", 8: "HD Graupel", 9: "Hail", 10: "Big Drops"}
CONFIG_FILE = "job_config.yaml"


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    idx = int(os.environ['SLURM_ARRAY_TASK_ID'])
    job = cluster.SlurmJob(cfg, "hmc")
    files = ["rg_files.txt", "temp_files.txt"]
    files = job.get_files(files, idx)
    rg_data, temp_data = _load_data(files[0], files[1])
    if cfg['source'] == "DWD":
        cfg['mp'] = temp_data.MP_PHYSICS  # DWD usually has no MP, but it uses Temp field of model
    _assert_data(rg_data, temp_data)
    time = dt.datetime.strptime(str(temp_data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")
    dolan_file = _get_output_files(time, cfg, cfg['mp'])
    dolan = _get_dolan(rg_data, temp_data)
    _save_dolan(dolan, time, cfg['mp'], dolan_file, cfg['source'])


def _load_data(rg_file, temp_file):
    rg_data = handles.load_xarray(rg_file)
    temp_data = handles.load_xarray(temp_file)
    return rg_data, temp_data


def _assert_data(rg_data, temp):
    rg_time = dt.datetime.strptime(rg_data.time, "%Y-%m-%d %H:%M:%S")
    temp_time = dt.datetime.strptime(str(temp['time'].values), "%Y-%m-%dT%H:%M:%S.%f000")
    assert (rg_time.date() == temp_time.date()), "Date missmatch"
    assert (rg_time.hour == temp_time.hour), "Hour missmatch"
    assert (rg_time.minute == temp_time.minute), "Minute missmatch"


def _get_output_files(time, cfg, mp_id):
    time_str = dt.datetime.strftime(time, "%H%M%S")
    dolan_folder = utils.make_folder(cfg['data']['HMC'] + os.sep + "Dolan" + os.sep + cfg['source'],
                                     mp_id=mp_id, radar="Isen", date=time.date())
    dolan_file = dolan_folder + time_str + ".nc"
    if os.path.exists(dolan_file):
        sys.exit()
    return dolan_file


def _get_dolan(df_data, temp_df):
    temp = temp_df['temperature'].values - 273.15
    dz_masked, dr_masked, kd_masked, rh_masked = _mask_data(df_data, DOLAN_LIMS)
    scores = csu_fhc.csu_fhc_summer(dz=dz_masked, zdr=dr_masked, rho=rh_masked, kdp=kd_masked,
                                    use_temp=True, band="C", return_scores=True, T=temp)
    fh_max = np.argmax(scores, axis=0) + 1
    fh_min = np.argmin(scores, axis=0) + 1
    mask_idx = np.where(fh_max == fh_min)
    fh_score = fh_max.copy().astype(float)
    fh_score[mask_idx] = np.nan
    return fh_score


def _mask_data(data, lim):
    dz_data = data['Zhh_corr'].values
    dz_data[dz_data < 5] = np.nan  # To filter noise/clutter
    dr_data = data['Zdr_corr'].values
    rh_data = data['RHOhv'].values
    kd_data = data['Kdp'].values
    zh_mask = np.where((dz_data >= lim['dz'][0]) & (dz_data <= lim['dz'][1]), dz_data, np.nan)
    zdr_mask = np.where((dr_data >= lim['dr'][0]) & (dr_data <= lim['dr'][1]), dr_data, np.nan)
    kdp_mask = np.where((kd_data >= lim['kd'][0]) & (kd_data <= lim['kd'][1]), kd_data, np.nan)
    rh_mask = np.where((rh_data >= lim['rh'][0]) & (rh_data <= lim['rh'][1]), rh_data, np.nan)
    nan_mask = np.isnan(zh_mask) | np.isnan(zdr_mask) | np.isnan(kdp_mask) | np.isnan(rh_mask)
    dz_masked = np.ma.masked_array(dz_data, mask=nan_mask, fill_value=np.nan).filled()
    dr_masked = np.ma.masked_array(dr_data, mask=nan_mask, fill_value=np.nan).filled()
    kd_masked = np.ma.masked_array(kd_data, mask=nan_mask, fill_value=np.nan).filled()
    rh_masked = np.ma.masked_array(rh_data, mask=nan_mask, fill_value=np.nan).filled()
    return dz_masked, dr_masked, kd_masked, rh_masked


def _save_dolan(data, time, mp_id, output_file, source):
    data_attrs = {'keys': str(DOLAN_KEYS)}
    data_dict = {"HID": (["height", "y", "x"], data, data_attrs)}
    df_attrs = {'mp_id': mp_id, 'source': source, 'method': "Dolan"}
    _save(data_dict, time, output_file, df_attrs)


def _save(data_dict, time, output, attrs):
    dataset = xr.Dataset(data_dict)
    dataset.attrs['MP_PHYSICS'] = attrs['mp_id']
    dataset.attrs['source'] = attrs['source']
    dataset.attrs['method'] = attrs['method']
    time_str = str(dt.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S"))
    dataset.attrs['time'] = time_str
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in dataset.variables}
    dataset.to_netcdf(output, encoding=encoding)


if __name__ == "__main__":
    _main(CONFIG_FILE)
