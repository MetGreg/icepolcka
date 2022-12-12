""" Interpolate temperature to regular grid

This script takes the original model output temperature and interpolates it to the regular grid.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg data path
    database: RG
      - The rg database file path
    data: WRF
      - The wrf data path
    database: WRF
      - The wrf database file path
    data: CRSIM
      - The CR-SIM data path
    database: CRSIM
      - The CR-SIM database file path
    data: TEMP
      - The output temperature data path
    masks: RF
      - The path to the rf mask
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be processed
    source
      - The input data source ('MODEL' or 'DWD')
    update
      - Whether to update the database with new files
    exe
      - The python executable
    temp: workdir
      - The cluster working directory
    temp: script
      - The actual python script the is executed from the cluster

"""
import subprocess

from icepolcka_utils.database import interpolations, main, models
from icepolcka_utils import cluster, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    wrf_handles, _, _ = models.get_wrf_handles(cfg)
    crsim_handles = main.get_handles(models.CRSIMDataBase, cfg, "CRSIM", hm="all", mp_id=cfg['mp'],
                                     radar=cfg['radar'])
    rg_handles = main.get_handles(interpolations.RGDataBase, cfg, "RG", mp_id=cfg['mp'],
                                  radar=cfg['radar'], source=cfg['source'])
    assert len(wrf_handles) == len(rg_handles) == len(crsim_handles), "Length of handles not equal!"
    job = cluster.SlurmJob(cfg, 'temp', mem="1G", time="00:15:00", exe=cfg['exe'],
                           script=cfg['temp']['script'])
    filenames = {'wrf_files.txt': [h['file_path'] for h in wrf_handles],
                 'rg_files.txt': [h['file_path'] for h in rg_handles],
                 'crsim_files.txt': [h['file_path'] for h in crsim_handles]}
    job.write_files(filenames)
    batch_path = job.prepare_job(cfg_file)
    arg = "--array=0-" + str(len(wrf_handles) - 1)
    subprocess.run(["sbatch", arg, batch_path], check=True)


if __name__ == "__main__":
    _main(CONFIG_FILE)
