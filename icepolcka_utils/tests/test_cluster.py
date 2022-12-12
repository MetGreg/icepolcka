"""Tests for the cluster module"""
import os
import unittest

from tests import utils as test_utils

from icepolcka_utils import cluster, utils


class SlurmJobTest(unittest.TestCase):
    """Tests for the SlurmJob class"""
    def setUp(self):
        self.tmp = utils.make_folder("tmp")
        self.db_path = utils.make_folder("db")
        self.config_file = self.tmp + "test.yaml"
        cfg = self._write_config()
        self.job = cluster.SlurmJob(cfg, "test", mem="1KB")

    def tearDown(self):
        test_utils.delete_content(self.tmp)
        test_utils.delete_content(self.db_path)

    def test_prepare_job_creates_two_files(self):
        """Test if the job_folder is created with two files (batch script and config file)"""
        self.job.prepare_job(self.config_file)
        self.assertEqual(len(os.listdir(self.job.job_folder)), 2, "Expected exactly two files")

    def test_write_files_copies_a_test_file_to_expected_location(self):
        """Test if a file is written at expected output"""
        test_output = "test.txt"
        test_handles = [{'file_path': ["test.txt"]}]
        data_dict = {test_output: test_handles}
        self.job.write_files(data_dict)
        self.assertTrue(os.path.exists(self.job.job_folder + test_output))

    def test_get_files_reads_filename_correctly(self):
        """Test if the loaded filename is correct"""
        test_file = self.tmp + "test.txt"
        test_line = "test.nc"
        with open(test_file, "w", encoding="utf-8") as f_out:
            f_out.write(test_line + "\n")
        filenames = [test_file]
        files_out = self.job.get_files(filenames, 0)
        self.assertEqual(files_out[0], test_line)

    def _write_config(self):
        cfg = test_utils.create_config(self.tmp, self.db_path + "test.db")
        cfg['test'] = {'workdir': self.tmp}
        test_utils.write_config(cfg, self.config_file)
        return cfg


if __name__ == "__main__":
    unittest.main()
