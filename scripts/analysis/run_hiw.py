"""Send hiw job to cluster

High impact weather statistics are calculated on the cluster. This script prepares the job and
sends it to the cluster. The script is designed to work on a daily basis: the start- and
end time must always be from 00:00:00 to 23:59:59.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg data path
    database: RG
      - The rg database file path
    data: HMC
      - The hmc data path
    database: HMC
      - The hmc database file path
    data: WRF
      - The wrf data path
    database: WRF
      - The wrf database file path
    output: HIW
      - The output path
    masks: RF
      - The path to the rf mask
    masks: Distance
      - The path to the distance mask
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    update
      - Whether to update the database with new files
    exe
      - The python executable
    hiw: workdir
      - The cluster working directory
    hiw: script
      - The actual python script the is executed from the cluster
    wrf_hgt
      - The height index, at which the WRF data is analyzed
    hmc_hgt
      - The height index, at which the HMC data is analyzed

"""
import subprocess

from icepolcka_utils import cluster, utils
from icepolcka_utils.database import algorithms, interpolations, main


CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _main(cfg_file):
    cfg = utils.get_cfg(cfg_file)
    time_diff = cfg['end'] - cfg['start']
    _update_db(cfg)
    assert time_diff.days == 0 and time_diff.seconds == 86399, \
        "Only a time range of exactly 1 day (minus one second) is allowed"

    # All simulations
    for mp_id in [8, 28, 10, 30, 50]:
        cfg['mp'] = str(mp_id)
        _run_job(cfg, cfg_file, "MODEL", "wrf", "11G")
        _run_job(cfg, cfg_file, "MODEL", "Dolan", "2G")

    # DWD
    cfg['mp'] = "None"
    cfg['source'] = "DWD"
    _run_job(cfg, cfg_file, "DWD", "Dolan", "2G")


def _update_db(cfg):
    print("Updating")
    main.update_db(algorithms.HMCDataBase, cfg, "HMC")
    main.update_db(interpolations.RGDataBase, cfg, "RG")


def _run_job(cfg, cfg_file, source, method, mem):
    time = "3:00:00"
    job_name = "hiw_" + method
    if method == "wrf":
        hgt = cfg['wrf_hgt']
    else:
        hgt = cfg['hmc_hgt']
    job = cluster.SlurmJob(cfg, "hiw", job_name, mem=mem, time=time, exe=cfg['exe'],
                           script=cfg['hiw']['script'])
    batch_path = job.prepare_job(cfg_file, source, method, cfg['mp'], str(hgt))
    subprocess.run(["sbatch", batch_path], check=True)


if __name__ == "__main__":
    _main(CONFIG_FILE)
