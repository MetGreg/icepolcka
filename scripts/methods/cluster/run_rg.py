"""Send job for RegularGrid interpolation to cluster

This script sends a job for the interpolation of radar data to a RegularGrid
to the cluster.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import shutil
import subprocess
import datetime as dt

from icepolcka_utils.data_base import WRFDataBase, RFDataBase, DWDDataBase
from icepolcka_utils.utils import load_config


def get_data_base(cfg):
    """Get data base

    The data base class, as well as some other settings (microphysics, radar
    name) depend on the source of the data (DWD or MODEL). This function returns
    the corresponding settings. The input configuration dictionary must contain
    all keywords necessary.

    For an explanation on how to use the configuration file, see the README
    file.

    Args:
        cfg (dict): Configuration dictionary.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        (str, str, type, int, str)
            1) Path to data.
            2) Path to data base file.
            3) Data base class.
            4) WRF ID of microphysics scheme.
            5) Radar name.

    """
    print("Getting data base")
    if cfg['source'] == "DWD":
        key = "DWD"
        db_class = DWDDataBase
        mp = None
        radar = "Isen"
    elif cfg['source'] == "MODEL":
        key = "RF"
        db_class = RFDataBase
        mp = cfg['mp']
        radar = cfg['radar']
    else:
        raise AssertionError("Only 'DWD' or 'MODEL' possible for the source "
                             "configuration parameter")
    data_path = cfg['data'][key]
    db_path = cfg['database'][key]

    return data_path, db_path, db_class, mp, radar


def prep_folder(start, end, mp, radar, workdir, cfg_file):
    """Prepare job folder

    Prepares the job folder by creating the working directory (if it doesn't
    exist) and defining the name of the job. Also copies the config file to
    the job folder.

    Args:
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        workdir (str): Path to parent directory where the job is executed.
        cfg_file (str): Path to configuration file.

    Returns:
          (str, str):
            1) Name of the job.
            2) Path to the subdirectory where the job is executed.

    """
    print("Preparing job folder")
    if mp is None:
        mp_str = "DWD"
    else:
        mp_str = "MP" + str(mp)
    start_str = str(start).replace(":", "").replace(" ", "_")
    end_str = str(end).replace(":", "").replace(" ", "_")
    job_name = mp_str + "_" + radar + os.sep + start_str + "_TO_" + end_str \
        + os.sep
    job_folder = workdir + "job_" + job_name + os.sep
    try:
        os.makedirs(job_folder)
    except FileExistsError:
        pass
    shutil.copy(cfg_file, job_folder + os.sep + "job_config.yaml")
    return job_name, job_folder


def get_data(DataBase, path, db, update, recheck, start, end, source, mp,
             radar):
    """Get data

    Finds WRF data corresponding to the configured input.

    Args:
        DataBase (type): Database object. Either DWDDataBase or RFDataBase.
        path (str): Path to CR-SIM data.
        db (str): Path to CR-SIM data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        source (str): Whether 'DWD' or 'MODEL' data is processed.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Name of radar.

    Raises:
        AssertionError: When source argument is neither 'DWD' or 'MODEL'.

    Returns:
        list:
            List containing ResultHandles of corresponding data within
            configured time range.

    """
    print("Getting data")
    with DataBase(path, db, update=update, recheck=recheck) as data_base:
        if source == "DWD":
            handles = data_base.get_data(start, end)
        elif source == "MODEL":
            handles = data_base.get_data(start, end, mp_id=mp, radar=radar)
        else:
            raise AssertionError("Only 'DWD' or 'MODEL' possible for the "
                                 "source configuration parameter")
    return handles


def get_wrf_grid(path, db, update, recheck):
    """ Get WRF lon/lat grid

    The script assumes that the WRF lon/lat grid is the same even if the
    WRF data does not come from the same time as the currently processed time
    step. The WRF grid was left untouched throughout my simulations, that's why
    this is not making an error in my case. Other users should be careful here,
    if their grid changes during the time period that is processed.

    Args:
        path (str): Path to WRF data files.
        db (str): Path to WRF data base file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.

    Returns:
        ResultHandle:
            WRF data that includes the WRF grid.

    """
    print("Getting WRF grid")
    with WRFDataBase(path, db, update=update, recheck=recheck) as grid_data:
        grid_handle = grid_data.get_latest_data(domain="Munich")[0]
    return grid_handle


def write_files(handles, grid, job_folder):
    """Write file names and times to txt files

    Writes all file names and times to txt files, one line for each file or
    time. The cluster array job will later access these files based on
    the job indices.

    Args:
        handles (list): List of ResultHandles corresponding to CR-SIM data
            files.
        grid (ResultHandle): WRF Grid that includes the
            Lon/Lat coordinates.
        job_folder (str): Path to the directory where the job will be executed.

    """
    print("Writing files")
    wrf_file = job_folder + os.sep + "wrf_file.txt"
    list_files = job_folder + os.sep + "filenames.txt"
    list_times = job_folder + os.sep + "filetimes.txt"
    with open(wrf_file, "w") as file_handle:
        file_handle.write("%s\n" % grid['clouds']['file_path'])
    with open(list_files, "w") as file_handle:
        for handle in handles:
            file_handle.write("%s\n" % handle['file_path'])
    with open(list_times, "w") as file_handle:
        for handle in handles:
            time_str = dt.datetime.strftime(handle['time'], "%Y-%m-%d_%H%M%S")
            file_handle.write("%s\n" % time_str)


def create_batch_script(job_folder, job_name, radar, exe, script):
    """Prepare batch script

    Prepares the batch script that is used to send a job to the cluster.

    Args:
        job_folder (str): Path to the folder where the job is executed.
        job_name (str): Name of the job.
        radar (str): Radar name.
        exe (str): Path to the python executable
        script (str): Script that will be executed on cluster. This is a
            python script that actually starts the radar filter script with
            the correct settings.

    Returns:
        str:
            Path to the batch script.

    """
    print("Creating batch script")
    time_lim = "24:00:00"
    ram = "5G"

    if radar == "Mira35":
        ram = "10G"
        time_lim = "80:00:00"

    # Define job file names
    job_name = "rg_" + job_name
    batch_file = job_folder + "main"

    # Write batch script
    with open(batch_file, "w") as f:
        f.write('''\
#!/bin/bash -l
#SBATCH --partition=met-ws,met-cl,cluster
#SBATCH -J {}
#SBATCH -D {}
#SBATCH --ntasks=1
#SBATCH --mem={}
#SBATCH --nodes=1
#SBATCH --mail-type=end
#SBATCH --mail-user=gregor.koecher@lmu.de
#SBATCH --time={}

module load localflock

EXE={}
SCRIPT={}

$EXE $SCRIPT

        '''.format(job_name, job_folder, ram, time_lim, exe, script))
    return batch_file


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    data_path, db_path, db_class, mp, radar = get_data_base(cfg)
    job_name, job_folder = prep_folder(cfg['start'], cfg['end'], mp, radar, 
                                       cfg['rg']['workdir'], cfg_file)
    handles = get_data(db_class, data_path, db_path, cfg['update'],
                       cfg['recheck'], cfg['start'], cfg['end'],
                       cfg['source'], mp, radar)
    grid_ds = get_wrf_grid(cfg['data']['WRF'], cfg['database']['WRF'],
                           cfg['update'], cfg['recheck'])

    write_files(handles, grid_ds, job_folder)
    batch_path = create_batch_script(job_folder, job_name, radar, cfg['exe'], 
                                     cfg['rg']['script'])
    subprocess.run(["sbatch", batch_path])


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
