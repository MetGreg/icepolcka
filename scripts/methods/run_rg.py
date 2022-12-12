"""Send job for RegularGrid interpolation to cluster

This script transforms data (radar data or model data after applying the radar_filter) to a
regular Cartesian grid that is specified in the configuration file. For example:

cart_grid:
    z_min: -100
    z_max: 15000
    vert_res: 100

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RG
      - The rg output path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    radar
      - Name of the radar to be processed
    source
      - The input data source ('MODEL' or 'DWD')
    update
      - Whether to update the CR-SIM database with new files
    exe
      - The python executable
    rg: workdir
      - The cluster working directory
    rg: script
      - The actual python script the is executed from the cluster
    sites
      - Site coordinates (lon, lat, alt) of simulated radar (e.g., 'sites: Isen')
    cart_grid
      - Cartesian grid specifications (see explanation above)


If the data source is 'MODEL':

    data: RF
      - The rf data path
    database: RF
      - The rf database file path
    mp
      - MP scheme of the rf data to be processed


If the data source is 'DWD':

    data: DWD
      - The DWD data path
    database: DWD
      - The DWD database file path

"""
import subprocess
import datetime as dt

from icepolcka_utils import cluster, utils
from icepolcka_utils.database import interpolations, main, radars

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _main(cfg_file):
    print("Starting main")
    file_path = "/project/meteo/work/Gregor.Koecher/icepolcka/data/wrf/icepolcka/2019/05/28/MP8/" \
                "clouds_d03_2019-05-28_120000"
    cfg = utils.get_cfg(cfg_file)
    handles = _get_data(cfg)
    job = _prepare_job(cfg)
    filenames = {'wrf_file.txt': [file_path], 'filenames.txt': [h['file_path'] for h in handles],
                 'filetimes.txt': [dt.datetime.strftime(h['time'], "%Y-%m-%d_%H%M%S") for h in
                                   handles]}
    job.write_files(filenames)
    batch_path = job.prepare_job(cfg_file)
    subprocess.run(["sbatch", batch_path], check=True)


def _get_data(cfg):
    if cfg['source'] == "DWD":
        handles = main.get_handles(radars.DWDDataBase, cfg, "DWD")
    elif cfg['source'] == "MODEL":
        handles = main.get_handles(interpolations.RFDataBase, cfg, "RF", mp_id=cfg['mp'],
                                   radar=cfg['radar'])
    else:
        raise AssertionError("Only DWD or MODEL possible as data source")
    return handles


def _prepare_job(cfg):
    time = "07:00:00"
    mem = "8G"

    # DWD does not have a constant source grid, which means the interpolation takes longer
    if cfg['source'] == "DWD":
        time = "12:00:00"

    job = cluster.SlurmJob(cfg, "rg", mem=mem, time=time, exe=cfg['exe'],
                           script=cfg['rg']['script'])
    return job


if __name__ == "__main__":
    _main(CONFIG_FILE)
