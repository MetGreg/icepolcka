"""Run CR-SIM

Using this script, CR-SIM simulations will be queued to the cluster,
depending on the config.

The script will find all corresponding WRF input files and start a simulation
for each according to the given configuration. These simulations are sent to the
cluster.

Note: The PARAMETER file that corresponds to the input configuration is
    searched within the params-folder. The PARAMETER files must be saved in
    specific sub folders (X denotes the WRF ID of the MP scheme):
        params/MPX/radar/PARAMETERS

For an explanation on how to use the configuration file, see the README file.

"""
import os
import subprocess
import datetime as dt

from icepolcka_utils.data_base import WRFDataBase
from icepolcka_utils.utils import load_config, make_folder


def get_handles(path, db, update, recheck, start, end, mp):
    """Get WRF data

    Finds WRF data corresponding to the configured input.

    Args:
        path (str): Path to CR-SIM data.
        db (str): Path to CR-SIM data file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.
        start (datetime.datetime):  Start time [UTC] of configured time range.
        end (datetime.datetime):  End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List containing ResultHandles of corresponding data within
                configured time range.

    """
    print("Getting WRF data")
    with WRFDataBase(path, db, update=update, recheck=recheck) \
            as wrf_data:
        handles = wrf_data.get_data(start, end, domain="Munich", mp_id=mp)
    return handles


def create_batch_script(job_name, job_folder, threads, ram, time, p_file,
                        wrfinput, exe, output):

    """Prepare batch script

    Prepares the batch script that is used to send a job to the cluster.

    Args:
        job_folder (str): Path to the folder where the job is executed.
        job_name (str): Name of the job.
        threads (int): Number of threads for cluster job.
        ram (str): RAM that is reserved for the cluster job.
        time (str): Time limit for cluster job in the format HH:MM:SS.
        p_file (str): Path to CR-SIM parameter file.
        wrfinput (str): Path to WRF output file that is used as CR-SIM input.
        exe (str): Path to CR-SIM executable.
        output (str): Path to the output file.

    Returns:
        str:
            Path to the batch script.

    """
    # Define job file names
    job_name = "crsim_" + job_name
    log_file = job_folder + job_name + ".out"
    try:
        os.makedirs(job_folder)
    except FileExistsError:
        pass
    batch_file = job_folder + "main"

    # Write batch script
    with open(batch_file, "w") as f:
        f.write('''\
#!/bin/bash -l
#SBATCH --partition=met-ws,met-cl,cluster
#SBATCH -o {}
#SBATCH -J {}
#SBATCH -D {}
#SBATCH --ntasks={}
#SBATCH --mem={}
#SBATCH --nodes=1
#SBATCH --mail-type=fail
#SBATCH --mail-user=gregor.koecher@lmu.de
#SBATCH --time={}

PARAMETERS={}
INPUT={}
OUTPUT={}

module load localflock

{} $PARAMETERS $INPUT $OUTPUT
        '''.format(log_file, job_name, job_folder, threads, ram, time, p_file,
                   wrfinput, output, exe))
    return batch_file


def set_cluster_res(mp, handle_dict, model_time):
    """Set cluster resources

    The cluster job needs resources depending on the radar and the
    microphysics scheme that is simulated. This job sets the corresponding
    resource variables (time and ram).

    Args:
        mp (int): WRF ID of microphysics scheme.
        handle_dict (dict): Dictionary containing the wrf input file name.
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
    clouds_file = handle_dict['clouds']['file_path']
    wrfinput = clouds_file
    time = "03:00:00"
    threads = 8

    # Set resources for Thompson scheme
    if mp == 8:
        ram = "22G"

    # Set resources for Morrison scheme
    elif mp == 10:
        ram = "6G"

    # Set resources for Thompson aerosol aware scheme
    elif mp == 28:
        ram = "22G"

    # Set resources for Spectral Bin Scheme
    elif mp == 30:
        threads = 1  # SBM works only with threads = 1
        ram = "11G"

        # SBM needs a wrfmp file next to the wrfout file. Check that this
        # file has the correct time stamp corresponding to the wrfout file.
        wrfmp_handle = handle_dict['wrfmp']
        wrfmp_file = wrfmp_handle['file_path']
        assert model_time == wrfmp_handle['start_time'], \
            "Couldn't find corresponding wrfmp file"
        wrfinput = clouds_file + "," + wrfmp_file

    # Set resources for P3 scheme
    elif mp == 50:
        threads = 1  # P3 only works with threads = 1
        time = "40:00:00"
        ram = "8G"
    else:
        raise AssertionError("MP scheme ID not known. Possible are: 8, 10, "
                             "28, 30, 50")

    return threads, time, ram, wrfinput


def main(cfg_file):
    print("Starting main")
    cfg = load_config(cfg_file)
    handles = get_handles(cfg['data']['WRF'], cfg['database']['WRF'],
                          cfg['update'], cfg['recheck'], cfg['start'],
                          cfg['end'], cfg['mp'])

    print("Sending CR-SIM job for each time step")
    for handle_dict in handles:
        handle = handle_dict['clouds']
        model_time = handle['start_time']
        time_str = dt.datetime.strftime(model_time, "%Y-%m-%d_%H%M%S")
        output_folder = make_folder(cfg['data']['CRSIMOut'], cfg['mp'],
                                    cfg['radar'],  model_time)
        str_time = dt.datetime.strftime(model_time, "%H%M%S")
        output_file = output_folder + str_time + ".nc"
        if os.path.exists(output_file):
            continue
        print(output_file)
        threads, time, ram, wrfinput = set_cluster_res(cfg['mp'], handle_dict,
                                                       model_time)
        job_name = "MP" + str(cfg['mp']) + "_" + cfg['radar'] + "_" \
                   + str(time_str)
        job_folder = cfg['crsim']['workdir'] + "job_" + job_name + os.sep
        job_params = cfg['crsim']['params'] + os.sep + "MP" \
            + str(cfg['mp']) + os.sep + cfg['radar'] + os.sep + "PARAMETERS"
        batch_path = create_batch_script(job_name, job_folder, threads, ram,
                                         time, job_params, wrfinput,
                                         cfg['crsim']['exe'], output_file)
        subprocess.run(["sbatch", batch_path])


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
