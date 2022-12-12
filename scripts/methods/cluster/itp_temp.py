""" Interpolate temperature to regular grid

This script takes the original model output temperature and interpolates it to the regular grid.

"""
import os
import sys
import datetime as dt

import numpy as np
import wradlib as wrl
import xarray as xr
from netCDF4 import Dataset
from wrf import getvar

from icepolcka_utils import cluster, utils
from icepolcka_utils.database import handles

CONFIG_FILE = "job_config.yaml"


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    mask = np.load(cfg['masks']['RF']).astype(bool)
    idx = int(os.environ['SLURM_ARRAY_TASK_ID'])
    job = cluster.SlurmJob(cfg, "temp")
    files = ["wrf_files.txt", "rg_files.txt", "crsim_files.txt"]
    files = job.get_files(files, idx)
    wrf_data, rg_data, crsim_data = _load_data(files[0], files[1], files[2])
    _assert_data(wrf_data, rg_data, crsim_data)
    time = dt.datetime.strptime(str(crsim_data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")
    time_str = dt.datetime.strftime(time, "%H%M%S")
    output = utils.make_folder(cfg['data']['TEMP'], mp_id=crsim_data.MP_PHYSICS, date=time.date())
    output = output + time_str + ".nc"
    if os.path.exists(output):
        sys.exit()
    temp_itp = _interpolate(wrf_data, rg_data, crsim_data)
    _save(temp_itp, time, crsim_data.MP_PHYSICS, mask, output)


def _load_data(wrf_file, rg_file, crsim_file):
    wrfin = Dataset(wrf_file)
    rg_data = handles.load_xarray(rg_file)
    crsim_data = handles.load_xarray(crsim_file)
    return wrfin, rg_data, crsim_data


def _assert_data(wrf_data, rg_data, crsim_data):
    wrf_time = wrf_data['Times'][0].data
    wrf_time_str = [t.decode("utf-8") for t in wrf_time]
    wrf_time = "".join(wrf_time_str)
    wrf_time = dt.datetime.strptime(wrf_time, "%Y-%m-%d_%H:%M:%S")
    wrf_mp = wrf_data.MP_PHYSICS
    rg_mp = rg_data.MP_PHYSICS
    rg_time = dt.datetime.strptime(rg_data.time, "%Y-%m-%d %H:%M:%S")
    crsim_time = dt.datetime.strptime(str(crsim_data['time'].values), "%Y-%m-%dT%H:%M:%S.%f000")
    crsim_mp = int(crsim_data.MP_PHYSICS)
    assert wrf_time == rg_time == crsim_time, "Time missmatch"
    assert wrf_mp == rg_mp == crsim_mp, "MP missmatch"


def _interpolate(wrf_data, rg_data, crsim_data):
    temp = getvar(wrf_data, "tk")[:-10]
    z_rg = rg_data['height'].values
    temp_itp = np.empty((z_rg.shape[0], 360, 360))
    for x_idx in range(360):
        for y_idx in range(360):
            z_crsim = crsim_data['height'].values[:, x_idx, y_idx]
            itp = wrl.ipol.Idw(z_crsim, z_rg)
            z_itp = itp(temp[:, y_idx, x_idx].values)
            temp_itp[:, y_idx, x_idx] = z_itp
    return temp_itp


def _save(temp, time, mp_id, mask, output):
    temp_masked = np.where(~mask, temp, np.nan)
    data_dict = {"temperature": (["height", "y", "x"], temp_masked)}
    dataset = xr.Dataset(data_dict)
    dataset['time'] = time
    dataset.attrs['MP_PHYSICS'] = mp_id
    encoding = {k: {'zlib': True, 'fletcher32': True} for k in dataset.variables}
    dataset.to_netcdf(output, encoding=encoding)


if __name__ == "__main__":
    _main(CONFIG_FILE)
