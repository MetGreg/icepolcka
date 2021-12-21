"""Send job for shrinking CR-SIM data to cluster

CR-SIM data is big. Not all the data that is produced by CR-SIM is necessary
for my work. That's why I shrink the CR-SIM output and remove the unnecessary
data.

This script does not do the actual shrinking, but only reads the configuration
file and then sends a job to the cluster that starts the actual shrink_data.py
script with the given configuration. The configuration is read here and not in
the actual shrink_data script, because this ensures the configuration is not
changing within the time until the shrink data script is started. (When the job
sits some time in the queue, the configuration file now can be changed for other
purposes, without affecting the shrink job.)

The current implementation assumes the date does not change. This makes it
simpler to find the CR-SIM out files by using the date. The script raises
therefore an AssertionError, if the date of the configured start and end time
differ.

For an explanation on how to use the configuration file, see the README file.

"""
import os
import subprocess

from icepolcka_utils.utils import load_config


def get_hms(mp):
    """Get hydrometeor list

    The hydrometeor class names depend on the microphysics scheme. This
    function returns a list of hydrometeor names that correspond to the
    microphysics scheme used.

    Args:
        mp (int): WRF ID of microphysics scheme.

    Returns:
        list:
            List of hydrometeor names corresponding to the microphysics
                scheme used.

    """
    print("Getting hydrometeor names")
    if mp == 50:
        hms = ["all", "parimedice", "rain", "smallice", "unrimedice",
        "graupel", "cloud"]
    else:
        hms = ["all", "cloud", "ice", "graupel", "rain", "snow"]
    return hms


def create_batch_script(start, end, mp, radar, hm, workdir, exe, script,
                        cfg_file):
    """Prepare batch script

    Prepares the batch script that is used to send a job to the cluster.

    Args:
        start (datetime.datetime): Start time [UTC] of configured time range.
        end (datetime.datetime): End time [UTC] of configured time range.
        mp (int): WRF ID of microphysics scheme.
        radar (str): Radar name.
        hm (str): Hydrometeor class name.
        workdir (str): Path to the folder where the sub folder is created for
            the job that will be executed.
        exe (str): Path to the python executable
        script (str): Script that will be executed on cluster. This is a
            python script that actually shrinks the data.
        cfg_file (str): Path to configuration file.

    Returns:
        str:
            Path to the batch script.

    """
    start_str = str(start).replace(" ", "_").replace(":", "")
    end_str = str(end).replace(" ", "_").replace(":", "")
    job_name = "shrink_" + "MP" + str(mp) + "_" + radar + "_" + hm + "_" \
               + start_str + "_" + end_str
    job_folder = workdir + "job_" + job_name + os.sep
    log_file = job_folder + job_name + ".out"
    try:
        os.makedirs(job_folder)
    except FileExistsError:
        pass

    batch_file = job_folder + "main"

    with open(batch_file, "w") as f:
        f.write('''\
#!/bin/bash -l
#SBATCH --partition=met-ws,met-cl,cluster
#SBATCH -o {}
#SBATCH -J {}
#SBATCH -D {}
#SBATCH --ntasks=1
#SBATCH --mem=2G
#SBATCH --nodes=1
#SBATCH --mail-type=fail
#SBATCH --mail-user=gregor.koecher@lmu.de
#SBATCH --time=8:00:00

EXE={}
SCRIPT={}
START={}
END={}
MP={}
RADAR={}
HM={}
CFG={}

$EXE $SCRIPT $START $END $MP $RADAR $HM $CFG
        '''.format(log_file, job_name, job_folder, exe, script, start_str,
                   end_str, mp, radar, hm, cfg_file))
    return batch_file


def main(cfg_file):
    cfg = load_config(cfg_file)
    assert cfg['start'].date() == cfg['end'].date(), "Only daily scripts " \
                                                     "allowed"

    hms = get_hms(cfg['mp'])
    print("Sending job for each hydrometeor")
    for hm in hms:
        print(hm)
        batch_script = create_batch_script(cfg['start'], cfg['end'], cfg['mp'],
                                           cfg['radar'], hm,
                                           cfg['shrink']['workdir'], cfg['exe'],
                                           cfg['shrink']['script'], cfg_file)
        subprocess.Popen(["sbatch", batch_script])


if __name__ == "__main__":
    config_file = "/home/g/Gregor.Koecher/.config/icepolcka/method_paper.yaml"
    main(config_file)
