"""Send job for hydrometeor classification to the cluster

This script sends a job for classification of hydrometeors to the cluster.

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg data path
    database: RG
      - The rg database file path
    data: TEMP
      - The temperature data path
    database: TEMP
      - The temperature database file path
    data: HMC
      - The output path
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
    hmc: workdir
      - The cluster working directory
    hmc: script
      - The actual python script the is executed from the cluster

"""
import subprocess

from icepolcka_utils import cluster, utils
from icepolcka_utils.database import interpolations, main

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _main(cfg_file):
    print("Starting main")
    cfg = utils.get_cfg(cfg_file)
    rg_handles = main.get_handles(interpolations.RGDataBase, cfg, "RG", mp_id=cfg['mp'],
                                  source=cfg['source'], radar=cfg['radar'])
    temp_handles = main.get_handles(interpolations.TempDataBase, cfg, "TEMP", mp_id=8)
    assert len(rg_handles) == len(temp_handles), "Length of handles not equal!"

    mem = "4G"

    job = cluster.SlurmJob(cfg, "hmc", mem=mem, time="00:10:00", exe=cfg['exe'],
                           script=cfg['hmc']['script'])
    filenames = {'rg_files.txt': [h['file_path'] for h in rg_handles],
                 'temp_files.txt': [h['file_path'] for h in temp_handles]}
    job.write_files(filenames)
    batch_path = job.prepare_job(cfg_file, cfg['hmc']['workdir'])
    arg = "--array=0-" + str(len(rg_handles) - 1)
    subprocess.run(["sbatch", arg, batch_path], check=True)


if __name__ == "__main__":
    _main(CONFIG_FILE)
