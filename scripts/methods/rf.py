""" Executes the radarfilter script

This script executes the actual radar filter script. It is designed to work
within a slurm array job. For each time step, one job with a specific index is
executed. This script finds the corresponding data file and time step over the
index from a file where the input files are listed.

This script creates subdirectories for all variables and runs the radar
filter script for each variable separately.

"""
import os
import shutil
import subprocess
import datetime as dt

VARIABLES = ["Zhh", "Zdr", "LDRh", "RHOhv", "Kdp", "Ah", "Adp"]


def get_files(idx):
    """Get the CR-SIM filename

    The file name and time is found corresponding to the index of the array job.

    Args:
        idx (int): Index of array job.

    Returns:
        (str, datetime.datetime):
            1) Path to CR-SIM file.
            2) CR-SIM file time stamp [UTC]

    """
    print("Getting files")
    with open("filenames.txt", "r") as file_handle:
        names = file_handle.readlines()

    with open("filetimes.txt", "r") as file_handle:
        times = file_handle.readlines()

    time = dt.datetime.strptime(times[idx].strip(), "%Y-%m-%d_%H%M%S")
    return names[idx].strip(), time


def prep_folder(workdir, idx, var):
    """Prepare job folder

    Prepares the job folder by making the subdirectories (if they don't
    exist) and copying the radar filter code and the parameter file to the
    directory.

    Args:
        workdir (str): Path to working directory.
        idx (int): Index of array job.
        var (str): Variable name.

    Returns:
          str:
            Path to the subdirectory where the job is executed.

    """
    sub_folder = workdir + os.sep + str(idx) + os.sep + var + os.sep
    rf_folder = workdir + os.sep + "radar_filter"
    param_file = workdir + os.sep + "RF_PARAMETERS"
    try:
        os.makedirs(sub_folder)
    except FileExistsError:
        pass
    for file_name in os.listdir(rf_folder):
        shutil.copy(rf_folder + os.sep + file_name, sub_folder)
    shutil.copy(param_file, sub_folder)
    return sub_folder


def set_params(sub_folder, date, crsim_file, var):
    """Create parameter file

    The radar filter script needs a parameter file, where some configurations
    are given. This configurations include: Input/output file, variable name,
    maximum radar range minimum and maximum azimuth angle, elevation angles.

    This function sets these settings by writing to the Parameter file within
    the job directory.

    Args:
        sub_folder (str): Path to sub folder of working directory for this job.
        date (datetime.datetime): Time step [UTC] of CR-SIM file.
        crsim_file (str): Path to input CR-SIM file.
        var (str): Name of variable.

    """
    param_file = sub_folder + os.sep + "RF_PARAMETERS"
    str_time = dt.datetime.strftime(date, "%H%M%S")

    # Open the parameter file and write the simulation specific configs
    with open(param_file, "r") as f:
        params = f.readlines()
    output = params[14].strip()[1:-1] + str(date.year) + os.sep \
        + f"{date.month:02d}" + os.sep + f"{date.day:02d}" + os.sep \

    # Check if output exists already
    try:
        os.makedirs(output)
    except FileExistsError:
        pass

    output_file = output + os.sep + str_time + "_" + var + ".nc"
    if os.path.exists(output_file):
        return

    params[2] = "'" + crsim_file + "'" + "\n"
    params[4] = "'" + var + "'" + "\n"
    params[14] = "'" + output_file + "'" + "\n"
    with open(param_file, "w") as f:
        f.writelines(params)


def main():
    print("Starting main")
    idx = int(os.environ['SLURM_ARRAY_TASK_ID'])
    filename, filetime = get_files(idx)
    workdir = os.getcwd()
    print("Execute RF for all variables")
    for var in VARIABLES:
        print(var)
        sub_folder = prep_folder(workdir, idx, var)
        set_params(sub_folder, filetime, filename, var)
        os.chdir(sub_folder)
        subprocess.run(["./radar_filter"])


if __name__ == "__main__":
    main()
