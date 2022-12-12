"""Module that includes everything used for communication with the cluster"""
import os
import shutil

from icepolcka_utils import utils


class SlurmJob:
    """Slurm job handler

    Class to handle everything around jobs that are about to be sent to the cluster. Container for
    the job arguments. Creates the batch script that is executed to send a job to the cluster.

    :param cfg: Configuration dictionary.
    :type cfg: dict
    :param name: Name of the script. Used to look up corresponding configuration.
    :type name: str
    :param job_name: Name of the cluster job.
    :type job_name: str
    :param kwargs: Any further class attribute (name: value).

    Attributes:
        job_folder (str):
            Path to the folder where the job is executed.
        job_name (str):
            Name of the job. Default: None.
        exe (str):
            Path to executable.
        script (str):
            Script that will be executed on cluster. This is a python script that actually starts
            the interpolation script with the correct settings.
        mem (str):
            Memory reserved for the job (e.g. "5G").
        time (str):
            Time limit for the job (e.g. "00:05:00").
        threads (int):
            Number of cores to be used.

    """
    def __init__(self, cfg, name, job_name=None, **kwargs):
        if job_name is None:
            job_name = name
        self.job_name = self._get_job_name(cfg, job_name)
        self.job_folder = self._make_job_folder(cfg[name]['workdir'])
        self.mem = None
        self.time = None
        self.exe = None
        self.script = None
        self.threads = 1
        for key, value in kwargs.items():
            setattr(self, key, value)

    def prepare_job(self, cfg_file, *args):
        """Write batch script

        Writes the batch script that is used to send a job to the cluster.


        :param cfg_file: Path to configuration yaml file.
        :type cfg_file: str
        :param args: Optional arguments that are used to specify which data is processed by the job.
            Possible options documented below.

        Keyword Arguments:
            source (str):
                Source of data (DWD or MODEL).
            method (str):
                HMC method (Dolan or Pejcic).
            mp (str):
                WRF-ID of microphysics scheme.

        Returns:
            str:
                Path to the batch script.

        """
        shutil.copy(cfg_file, self.job_folder + os.sep + "job_config.yaml")
        batch_file = self.job_folder + os.sep + "main"
        batch_string = self._create_batch_string(*args)
        with open(batch_file, "w", encoding="utf-8") as batch_f:
            batch_f.write(batch_string)
        return batch_file

    def write_files(self, data_dict):
        """Write files with information needed by a cluster job to working directory of the job

        Sometimes, a cluster job needs specific information, such as which files to
        process. This method writes this information to a file in the working directory of
        the cluster job where it is then accessed by the job directly.

        :param data_dict: Keys are filenames, values are a list of rows that will be written to the
            file.
        :type data_dict: dict

        """
        for filename, entries in data_dict.items():
            working_file = self.job_folder + os.sep + filename
            with open(working_file, "w", encoding="utf-8") as f_out:
                for entry in entries:
                    f_out.write(f"{entry}\n")

    def _make_job_folder(self, workdir):
        job_folder = workdir + "job_" + self.job_name + os.sep
        return utils.make_folder(job_folder)

    def _create_batch_string(self, *args):
        log_file = self.job_folder + os.sep + self.job_name + ".out"
        batch_string = (
            f"#!/bin/bash -l \n"
            f"#SBATCH --partition=met-ws,met-cl,cluster \n"
            f"#SBATCH -o {log_file} \n"
            f"#SBATCH -J {self.job_name} \n"
            f"#SBATCH -D {self.job_folder} \n"
            f"#SBATCH --ntasks={self.threads} \n"
            f"#SBATCH --mem={self.mem} \n"
            f"#SBATCH --nodes=1 \n"
            f"#SBATCH --mail-type=fail \n"
            f"#SBATCH --mail-user=gregor.koecher@lmu.de \n"
            f"#SBATCH --time={self.time} \n"

            f"EXE={self.exe} \n"
            f"SCRIPT={self.script} \n"

            f"$EXE $SCRIPT"
            )

        # Sometimes, the scripts need arguments. These arguments are given as input to this method
        # via the *args argument and need to be appended to the batch_string to be executed.
        batch_string = (batch_string + " %s") % " ".join(args)
        return batch_string

    @staticmethod
    def get_files(file_list, idx):
        """Get filenames to be processed by the job from a list of files and a cluster job index

        Array cluster jobs work by sending multiple jobs to the cluster that differ only in terms
        of an index that corresponds to the job. This index is used to find the correct files to
        process, from a list of filenames.

        :param file_list: List of filenames that shall be accessed.
        :type file_list: list
        :param idx: Index of current array job.
        :type idx: int

        Returns:
            list:
                The filenames at the given job index. The length of this list corresponds to the
                length of the input file_list.

        """
        filenames = []
        for file in file_list:
            with open(file, "r", encoding="utf-8") as file_handle:
                files = file_handle.readlines()
                filenames.append(files[idx].strip())
        return filenames

    @staticmethod
    def _get_job_name(cfg, job_name):
        start_str = str(cfg['start']).replace(":", "").replace(" ", "_")
        end_str = str(cfg['end']).replace(":", "").replace(" ", "_")
        if "source" in cfg:
            job_name = job_name + "_" + cfg['source']
        if cfg['mp'] is not None:
            job_name = job_name + "_MP" + str(cfg['mp'])
        job_name = job_name + "_" + start_str + "_TO_" + end_str
        return job_name
