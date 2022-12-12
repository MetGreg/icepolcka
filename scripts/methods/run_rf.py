"""Send job for executing the radar filter script to cluster

The radarfilter is a script provided together with CR-SIM by the Aleksandra Tatarevic from the
Stonybrook University. It transforms the original Cartesian CR-SIM data to a radar grid. This script
executes this script by sending an array job to our cluster for all time steps within the configured
time range.

The radar filter script reads a PARAMETER file, where some configs are given, such as the spherical
grid characteristics (azimuth and elevation), or input/output files. These characteristics are set
by this script according to the radar that is simulated. The grid of the radar to be simulated
must be specified under 'sphere' in the configuration file.
For example, for the DWD Isen radar:
sphere:
    Isen:
        max_range: 144000
        min_az: 0
        max_az: 360
        elevs: [0.5, 0.8, 1.5, 2.5, 3.5, 4.5, 5.5, 8, 12, 17, 25]

The script opens a configuration.yaml file, where some configuration options are defined. The path
to this file is given at the beginning of this script as a global variable 'CONFIG_FILE'. An
example configuration file is part of the icepolcka repository.

In the configuration file, the following information must be given:

    data: RFOut
      - The rf output path
    data: CRSIM
      - The CR-SIM data path
    database: CRSIM
      - The CR-SIM database file path
    start
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    end
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    mp
      - MP scheme of the data to be processed
    radar
      - Name of the radar to be simulated
    update
      - Whether to update the database with new files
    exe
      - The python executable
    rf: workdir
      - The cluster working directory
    rf: script
      - The actual python script the is executed from the cluster
    rf: folder
      - The folder where the radar_filter code is located
    sphere
      - Radar grid specifics (see explanation above)

"""
import os
import shutil
import subprocess
import datetime as dt

from icepolcka_utils.database import main, models
from icepolcka_utils import cluster, utils

CONFIG_FILE = "/home/g/Gregor.Koecher/.config/icepolcka/paper2.yaml"


def _get_spherical_grid(spherical_grid, radar):
    """Get spherical grid

    Defines the spherical grid by extracting the grid definition from the spherical grid config
    dictionary.

    Args:
        spherical_grid (dict): Dictionary containing the spherical grid definition for each radar.
        radar (str): Radar name.

    Returns:
        (int, int, int, list):
            1) Maximum range of spherical grid [m].
            2) Minimum azimuth angle of spherical grid.
            3) Maximum azimuth angle of spherical grid.
            4) List of elevation angles of spherical grid.

    """
    print("""Getting spherical grid""")
    max_range = spherical_grid[radar]['max_range']
    min_az = spherical_grid[radar]['min_az']
    max_az = spherical_grid[radar]['max_az']
    elevs = spherical_grid[radar]['elevs']
    return max_range, min_az, max_az, elevs


def _prep_folder(job, rf_dir):
    """Prepare job folder

    Prepares the job folder by copying the radar filter code to the working directory.

    Args:
        job (SlurmJob): Cluster job object with information about the working directory.
        rf_dir (str): Path to the radar filter package.

    Returns:
          (str, str):
            1) Name of the job.
            2) Path to the subdirectory where the job is executed.

    """
    print("Preparing job folder")
    rf_subfolder = job.job_folder + os.sep + "radar_filter" + os.sep
    try:
        shutil.copytree(rf_dir, rf_subfolder)
    except FileExistsError:
        pass
    shutil.copy(rf_subfolder + os.sep + "RF_PARAMETERS", job.job_folder)


def _write_files(handles, job):
    """Write file names and times to txt files

    Writes all file names and times to txt files, one line for each file or time. The cluster array
    job will later access these files based on the job indices.

    Args:
        handles (list): List of ResultHandles corresponding to CR-SIM data files.
        job (SlurmJob): Cluster job object with information about the working directory.

    """
    print("Writing files")
    file_names = [handle['file_path'] for handle in handles]
    file_times = [dt.datetime.strftime(handle['time'], "%Y-%m-%d_%H%M%S") for handle in handles]
    job.write_files({"filenames.txt": file_names, "filetimes.txt": file_times})


def _set_params(job_folder, cfg, output):
    """Create parameter file

    The radar filter script needs a parameter file, where some configurations are given. The
    configurations include: Input/output file, variable name, maximum radar range minimum and
    maximum azimuth angle, elevation angles.

    This function sets these settings by writing to the Parameter file within the job directory.

    Args:
        job_folder (str): Path to job folder.
        cfg (dict): Configuration dictionary.
        output (str): Name of output file

    """
    print("Setting parameters")
    param_file = job_folder + os.sep + "RF_PARAMETERS"
    max_range, min_az, max_az, elevs = _get_spherical_grid(cfg['sphere'], cfg['radar'])

    # Open the parameter file and write the simulation specific configs
    with open(param_file, "r", encoding="utf-8") as f_in:
        params = f_in.readlines()
    params[8] = "0," + str(max_range) + ".0" + "\n"
    params[12] = str(min_az) + "," + str(max_az) + "," + "1" + "\n"
    params[14] = "'" + output + "'" + "\n"
    params[20] = str(len(elevs)) + "\n"
    params[22] = str(elevs)[1:-1].replace(" ", "") + "\n"
    with open(param_file, "w", encoding="utf-8") as f_out:
        f_out.writelines(params)


def _run_job(cfg, cfg_file, handles):
    time = "00:20:00"
    ram = "500M"

    # Mira needs more resources
    if cfg['radar'] == "Mira35":
        ram = "1G"
        time = "00:60:00"

    job_name = "rf_" + cfg['radar']
    job = cluster.SlurmJob(cfg, "rf", job_name, mem=ram, time=time, exe=cfg['exe'],
                           script=cfg['rf']['script'])
    _prep_folder(job, cfg['rf']['folder'])
    _write_files(handles, job)
    output_folder = utils.make_folder(cfg['data']['RFOut'], cfg['mp'], cfg['radar'])
    _set_params(job.job_folder, cfg, output_folder)
    batch_path = job.prepare_job(cfg_file)
    arg = "--array=0-" + str(len(handles) - 1)
    subprocess.run(["sbatch", arg, batch_path], check=True)


def _main(cfg_file):
    print("Starting Main")
    cfg = utils.get_cfg(cfg_file)
    handles = main.get_handles(models.CRSIMDataBase, cfg, "CRSIM", mp_id=cfg['mp'],
                               radar=cfg['radar'], hm="all")
    _run_job(cfg, cfg_file, handles)


if __name__ == "__main__":
    _main(CONFIG_FILE)
