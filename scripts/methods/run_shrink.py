"""Send job for shrinking CR-SIM data to cluster

CR-SIM data is big. Not all the data that is produced by CR-SIM is necessary for my work. That's
why I shrink the CR-SIM output and remove the unnecessary data.

This script does not do the actual shrinking, but only reads the configuration file and then sends a
job to the cluster that starts the actual shrink_data.py script with the given configuration. The
configuration is read here and not in the actual shrink_data script, because this ensures the
configuration is not changing within the time until the shrink data script is started. (When the job
sits some time in the queue, the configuration file now can be changed for other purposes, without
affecting the shrink job.)

The current implementation assumes the date does not change. This makes it simpler to find the
CR-SIM out files by using the date. The script raises therefore an AssertionError, if the date of
the configured start and end time differ.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: CRSIMOut
      - Unprocessed CR-SIM data path
    data: CRSIM
      - Output path for shrinked CR-SIM data
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be simulated
    exe
      - The python executable
    shrink: workdir
      - The cluster working directory
    shrink: script
      - The actual python script that is executed from the cluster
    masks: Distance
      - The location of the distance mask
    cart_grid: z_max
      - The maximum height (m) of the grid

"""
import subprocess

from icepolcka_utils import cluster, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _get_hms(mp_id):
    """Get hydrometeor list

    The hydrometeor class names depend on the microphysics scheme. This function returns a list of
    hydrometeor names that correspond to the microphysics scheme used.

    Args:
        mp_id (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List of hydrometeor names corresponding to the microphysics scheme used.

    """
    print("Getting hydrometeor names")
    if mp_id == 50:
        hms = ["all", "parimedice", "rain", "smallice", "unrimedice", "graupel"]
    else:
        hms = ["all", "cloud", "ice", "graupel", "rain", "snow"]
    return hms


def _run_job(cfg, cfg_file, hm_name):
    job_name = "shrink_" + cfg['radar'] + "_" + hm_name
    ram = "2G"
    time = "08:00:00"
    job = cluster.SlurmJob(cfg, "shrink", job_name, mem=ram, time=time, exe=cfg['exe'],
                           script=cfg['shrink']['script'])
    batch_path = job.prepare_job(cfg_file, hm_name)
    subprocess.run(["sbatch", batch_path], check=True)


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    assert cfg['start'].date() == cfg['end'].date(), "Time cannot exceed 1 day"

    hms = _get_hms(cfg['mp'])
    print("Sending job for each hydrometeor")
    for hm_name in hms:
        print(hm_name)
        _run_job(cfg, cfg_file, hm_name)


if __name__ == "__main__":
    _main(CONFIG_FILE)
