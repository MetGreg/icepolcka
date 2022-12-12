"""Run CR-SIM

Using this script, CR-SIM simulations will be queued to the cluster, depending on the config.

The script will find all corresponding WRF input files and start a simulation for each according to
the given configuration. These simulations are sent to the cluster.

Note: The PARAMETER file that corresponds to the input configuration is
    searched within the params-folder. The PARAMETER files must be saved in
    specific sub folders (X denotes the WRF ID of the MP scheme):
        params/MPX/radar/PARAMETERS

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: CRSIMOut
      - The CR-SIM output path
    data: WRF
      - The wrf data path
    database: WRF
      - The wrf database file path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be simulated
    update
      - Whether to update the database with new data (bool)
    crsim: workdir
      - The cluster working directory
    crsim: exe
      - The CRSiM executable
    crsim: parameters
      - The CR-SIM parameter file locations

"""
import os
import subprocess
import datetime as dt

from icepolcka_utils.database import models
from icepolcka_utils import cluster, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _set_cluster_res(mp_id, cloud_handle, wrfmp_handle, model_time):
    """Set cluster resources

    The cluster job needs resources depending on the radar and the microphysics scheme that is
    simulated. This job sets the corresponding resource variables (time and ram).

    Args:
        mp_id (int): WRF ID of microphysics scheme.
        cloud_handle (ResultHandle): Clouds data.
        wrfmp_handle (ResultHandle): WRFmp data, if mp_id == 30
        model_time (datetime.datetime): Time of model output [UTC].

    Raises:
        AssertionError: When WRFmp handle does not fit to model time stamp.
        AssertionError: When MP ID is unknown.

    Returns:
        (int, str, str, str):
            1) Number of threads
            2) Time limit
            3) Reserved ram
            4) WRF input line for the CR-SIM simulation.

    """
    clouds_file = cloud_handle['file_path']
    wrfinput = clouds_file
    time = "03:00:00"
    threads = 8

    # Set resources for Thompson scheme
    if mp_id == 8:
        ram = "22G"

    # Set resources for Morrison scheme
    elif mp_id == 10:
        ram = "8G"

    # Set resources for Thompson aerosol aware scheme
    elif mp_id == 28:
        ram = "22G"

    # Set resources for Spectral Bin Scheme
    elif mp_id == 30:
        threads = 1  # SBM works only with threads = 1
        ram = "11G"

        # SBM needs a wrfmp file next to the wrfout file. Check that this file has the correct time
        # stamp corresponding to the wrfout file.
        wrfmp_file = wrfmp_handle['file_path']
        assert model_time == wrfmp_handle['start_time'], "Couldn't find corresponding wrfmp file"
        wrfinput = clouds_file + "," + wrfmp_file

    # Set resources for P3 scheme
    elif mp_id == 50:
        threads = 1  # P3 only works with threads = 1
        time = "66:00:00"
        ram = "10G"
    else:
        raise AssertionError("MP scheme ID not known. Possible are: 8, 10, 28, 30, 50")

    return threads, time, ram, wrfinput


def _run_job(cfg, cfg_file, cloud_handle, wrfmp_handle):
    model_time = cloud_handle['start_time']
    threads, time, ram, wrfinput = _set_cluster_res(cfg['mp'], cloud_handle, wrfmp_handle,
                                                    model_time)
    job_params = cfg['crsim']['params'] + os.sep + "MP" + str(cfg['mp']) + os.sep + cfg['radar'] + \
        os.sep + "PARAMETERS"
    output_file = _make_output_folder(cfg, cloud_handle)
    if os.path.exists(output_file):
        return
    job_name = "crsim_" + cfg['radar']
    job = cluster.SlurmJob(cfg, "crsim", job_name, mem=ram, time=time, exe='', threads=threads,
                           script=cfg['crsim']['exe'])
    batch_path = job.prepare_job(cfg_file, job_params, wrfinput, output_file)
    subprocess.run(["sbatch", batch_path], check=True)


def _make_output_folder(cfg, handle):
    model_time = handle['start_time']
    output_folder = utils.make_folder(cfg['data']['CRSIMOut'], cfg['mp'], cfg['radar'],
                                      model_time)
    str_time = dt.datetime.strftime(model_time, "%H%M%S")
    output_file = output_folder + str_time + ".nc"
    return output_file


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    cloud_handles, _, wrfmp_handles = models.get_wrf_handles(cfg, wrfmp=True)

    print("Sending CR-SIM job for each time step")
    wrfmp_handle = None
    for i, cloud_handle in enumerate(cloud_handles):
        if cfg['mp'] == 30:
            wrfmp_handle = wrfmp_handles[i]
        _run_job(cfg, cfg_file, cloud_handle, wrfmp_handle)


if __name__ == "__main__":
    _main(CONFIG_FILE)
