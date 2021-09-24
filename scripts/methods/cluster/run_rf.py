"""Send job for executing the radar filter script to cluster

The radarfilter is a script provided together with CR-SIM by the Aleksandra
Tatarevic from the Stonybrook University. It transforms the original Cartesian
CR-SIM data to a radar grid. This script executes this script by sending an
array job to our cluster for all time steps within the configured time range.

The radar filter script reads a PARAMETER file, where some configs are given,
such as the spherical grid characteristics (azimuth and elevation),
or input/output files. These characteristics are set by this script according
to the radar that is simulated.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import shutil
import subprocess
import datetime as dt

from icepolcka_utils.data_base import CRSIMDataBase
from icepolcka_utils.utils import load_config, make_folder


def get_crsim_data(path, db, update, recheck, start, end, mp, radar):
    """Get CR-SIM data

    Finds any CR-SIM data to get access to the grid. The CR-SIM and WRF grid
    are the same.

    Args:
        path (str): Path to CR-SIM data.
        db (str): Path to CR-SIM data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.

    Returns:
        list:
            List containing ResultHandles of corresponding data within
                configured time range.

    """
    print("Getting CR-SIM data")
    with CRSIMDataBase(path, db, recheck=recheck, update=update) as data_base:
        handles = data_base.get_data(start, end, mp_id=mp, radar=radar)
    return handles


def get_spherical_grid(spherical_grid, radar):
    """Get spherical grid

    Defines the spherical grid by extracting the grid definition from the
    spherical grid config dictionary.

    Args:
        spherical_grid (dict): Dictionary containing the spherical grid
            definition for each radar.
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


def prep_folder(start, end, mp, radar, workdir, rf_dir):
    """Prepare job folder

    Prepares the job folder by making the subdirectories (if they don't
    exist) and copying the radar filter code to the working directory.

    Args:
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        workdir (str): Path to parent directory where the job is executed.
        rf_dir (str): Path to the radar filter package.

    Returns:
          (str, str):
            1) Name of the job.
            2) Path to the subdirectory where the job is executed.

    """
    print("Preparing job folder")
    start_str = str(start).replace(":", "").replace(" ", "_")
    end_str = str(end).replace(":", "").replace(" ", "_")
    job_name = "MP" + str(mp) + "_" + radar + os.sep + start_str + "_TO_" + \
               end_str + os.sep
    job_folder = workdir + "job_" + job_name + os.sep
    rf_subfolder = job_folder + os.sep + "radar_filter" + os.sep
    try:
        os.makedirs(job_folder)
        shutil.copytree(rf_dir, rf_subfolder)
    except FileExistsError:
        pass
    shutil.copy(rf_subfolder + os.sep + "RF_PARAMETERS", job_folder)
    return job_name, job_folder


def write_files(handles, job_folder):
    """Write file names and times to txt files

    Writes all file names and times to txt files, one line for each file or
    time. The cluster array job will later access these files based on
    the job indices.

    Args:
        handles (list): List of ResultHandles corresponding to CR-SIM data
            files.
        job_folder (str): Path to the directory where the job will be executed.

    """
    print("Writing files")
    list_files = job_folder + os.sep + "filenames.txt"
    list_times = job_folder + os.sep + "filetimes.txt"
    with open(list_files, "w") as file_handle:
        for handle in handles:
            file_handle.write("%s\n" % handle['file_path'])
    with open(list_times, "w") as file_handle:
        for handle in handles:
            time_str = dt.datetime.strftime(handle['time'], "%Y-%m-%d_%H%M%S")
            file_handle.write("%s\n" % time_str)


def set_params(job_folder, max_range, min_az, max_az, elevs, output):
    """Create parameter file

    The radar filter script needs a parameter file, where some configurations
    are given. This configurations include: Input/output file, variable name,
    maximum radar range minimum and maximum azimuth angle, elevation angles.

    This function sets these settings by writing to the Parameter file within
    the job directory.

    Args:
        job_folder (str): Path to job folder.
        max_range (float): Maximum radar range to be considered.
        min_az (int): Minimum azimuth angle to be considered.
        max_az (int): Maximum azimuth angle to be considered.
        elevs (list): List of elevation angles.
        output (str): Name of output file

    """
    print("Setting parameters")
    param_file = job_folder + os.sep + "RF_PARAMETERS"

    # Open the parameter file and write the simulation specific configs
    with open(param_file, "r") as f:
        params = f.readlines()
    params[8] = "0," + str(max_range) + ".0" + "\n"
    params[12] = str(min_az) + "," + str(max_az) + "," + "1" + "\n"
    params[14] = "'" + output + "'" + "\n"
    params[20] = str(len(elevs)) + "\n"
    params[22] = str(elevs)[1:-1].replace(" ", "") + "\n"
    with open(param_file, "w") as f:
        f.writelines(params)


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
    time_lim = "00:20:00"
    ram = "500M"

    # Mira needs more resources
    if radar == "Mira35":
        ram = "1G"
        time_lim = "00:60:00"

    # Define job file names
    job_name = "rf_" + job_name
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


def main():
    print("Starting Main")
    cfg = load_config()
    handles = get_crsim_data(cfg['data']['CRSIM'], cfg['database']['CRSIM'],
                             cfg['update'], cfg['recheck'], cfg['start'],
                             cfg['end'], cfg['mp'], cfg['radar'])
    max_range, min_az, max_az, elevs = get_spherical_grid(cfg['sphere'],
                                                          cfg['radar'])
    job_name, job_folder = prep_folder(cfg['start'], cfg['end'], cfg['mp'],
                                       cfg['radar'], cfg['rf']['workdir'],
                                       cfg['rf']['folder'])
    write_files(handles, job_folder)
    output_folder = make_folder(cfg['data']['RFOut'], cfg['mp'], cfg['radar'])
    set_params(job_folder, max_range, min_az, max_az, elevs, output_folder)
    batch_path = create_batch_script(job_folder, job_name, cfg['radar'],
                                     cfg['exe'], cfg['rf']['script'])
    arg = "--array=0-" + str(len(handles) - 1)
    subprocess.run(["sbatch", arg, batch_path])


if __name__ == "__main__":
    main()
