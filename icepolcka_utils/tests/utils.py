"""Utility functions for the tests

TODO:
    Remove print statements of type in create_file.

"""
import os
import unittest
import datetime as dt

import yaml
import numpy as np

from icepolcka_utils import grid
from icepolcka_utils.database import tables


class GeneralDataBaseTest(unittest.TestCase):
    """Utility class for testing

    All Database classes have a very similar structure and hence, the corresponding tests use often
    the same lines to test for functionality. This class defines testing methods that are used
    multiple times by the different Database tests.

    """
    def setUp(self):
        self.db_path = "test_data" + os.sep + "test.db"
        self.wrong_path = "test_data" + os.sep + "wrong" + os.sep

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def time_test(self, db_class, data_path, method_name, exp_time, **kwargs):
        """Test get_data method

        Args:
            db_class (Child class of DataBase): Class that is tested.
            data_path (str): Path to data.
            method_name (str): Name of method to be tested.
            exp_time (datetime.datetime): Expected time of data [UTC].
            **kwargs:
                Arguments needed for the get_data method. Depend on the class that is tested.

        """
        with db_class(data_path, self.db_path, update=True) as db_open:
            handle = getattr(db_open, method_name)(**kwargs)

        data = self._load_data(handle)
        self._run_test(data, exp_time)

    def assert_datafiles(self, db_class, data_path, exp_files):
        """Test if number of data files is as expected

        Args:
            db_class (Child class of DataBase): Class that is tested.
            data_path (str): Path to data.
            exp_files (int): Number of expected data files.

        """
        with db_class(data_path, self.db_path, update=True) as _:
            pass
        session = tables.create_session(self.db_path)
        query = session.query(tables.Datafile).all()
        self.assertEqual(len(query), exp_files)
        session.close()

    def _run_test(self, data, exp_time):
        """Test if time is as expected and close data"""
        data_time = self._get_time(data)
        self.assertEqual(data_time, exp_time)
        try:
            data.close()
        except AttributeError:
            pass

    @staticmethod
    def _get_time(data):
        """Get time from the data. How to access the time depends on the data format"""
        raise NotImplementedError("Implemented by the corresponding specific test class")

    @staticmethod
    def _load_data(handle):
        """Load the data

        Loading data depends on the returned type. Sometimes a ResultHandle is returned, then a
        simple handle.load() loads the data. Sometimes, a list of ResultHandle is returned
        (e.g., if a method is tested that returns data from start to end time). In that case,
        just load the first entry for testing purposes.

        """
        # Sometimes handles is a list: then test first entry of this list
        try:
            data = handle.load()
        except AttributeError:
            data = handle[0].load()
        return data


def create_config(data_path=".", db_path=".", start=None, end=None, time="datetime"):
    """Create configuration dictionary

    Args:
        data_path (str): Path to data.
        db_path (str): Path to database.
        start (str): Start time [UTC].
        end (str): End time [UTC].
        time (str): Whether datetime or str time will be used.

    Returns:
        (dict): Configuration dictionary.

    """
    cfg = create_default_config(data_path, db_path, start, end)
    if time == "datetime":
        cfg['start'] = dt.datetime.strptime(cfg['start'], "%d.%m.%Y %H:%M:%S")
        cfg['end'] = dt.datetime.strptime(cfg['end'], "%d.%m.%Y %H:%M:%S")
        cfg['date'] = dt.datetime.strptime(cfg['date'], "%d.%m.%Y")
    return cfg


def create_default_config(data_path=".", db_path=".", start=None, end=None):
    """Creates a config dictionary

    Args:
        data_path (str): Path to data.
        db_path (str): Path to database.
        start (str): Start time [UTC].
        end (str): End time [UTC].

    Returns:
        (dict): Configuration dictionary.

    """
    if start is None:
        start = "01.07.2019 12:00:00"
    if end is None:
        end = "01.07.2019 12:00:00"

    cfg = {
        'start': start,
        'end': end,
        'date': start.split(" ")[0],
        'data': {
            'WRF': data_path + os.sep + "wrf",
            'HMC': data_path + os.sep + "hmc",
            'RG': data_path + os.sep + "rg",
            'RF': data_path + os.sep + "rf",
            'CRSIM': data_path + os.sep + "crsim",
            'TEMP': data_path + os.sep + "temp",
            'DWD': data_path + os.sep + "dwd",
            'TRACKS': data_path + os.sep + "tracks",
            },
        'database': {
            'WRF': db_path + os.sep + "wrf.db",
            'HMC': db_path + os.sep + "hmc.db",
            'RG': db_path + os.sep + "rg.db",
            'RF': db_path + os.sep + "rf.db",
            'CRSIM': db_path + os.sep + "crsim.db",
            'TEMP': db_path + os.sep + "temp.db",
            'DWD': db_path + os.sep + "dwd.db",
            'TRACKS': db_path + os.sep + "tracks.db",
            },
        'update': True,
        'mp': 8,
        'radar': "Isen",
        'source': "MODEL",
        'method': "Dolan",
        'masks': {
            'Distance': "test_data" + os.sep + "masks" + os.sep + "distance.npy",
            'RF': "test_data" + os.sep + "masks" + os.sep + "rf.npy"
            },
        }
    return cfg


def write_config(cfg, config_file):
    """Write data to config yaml

    Writes the configuration dictionary saved in the self.config_file attribute to a yaml file.

    Args:
         cfg (dict): Configuration dictionary.
         config_file (str): Configuration file.

    """
    with open(config_file, "w", encoding="utf-8") as outfile:
        yaml.dump(cfg, outfile, default_flow_style=False)


def delete_content(folder):
    """Delete files and folders at a given path

    Args:
        folder (str): Parent folder.

    """
    for root, _dirs, files in os.walk(folder, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        os.rmdir(root)


def make_pyart_grid(data, time):
    """Create a pyart grid for testing

    Args:
        data (numpy.ndarray):  3d array of data.
        time (datetime.datetime): Timestamp of data.

    Returns:
        (PyArtGrid): PyArtGrid constructed from data and time.

    """
    time = int(dt.datetime.timestamp(time))
    x_grid = {'data': np.arange(0, 2001, 1000)}
    y_grid = {'data': np.arange(0, 2001, 1000)}
    z_grid = {'data': np.array([0])}
    lon = np.array([[10, 10.5, 11], [10, 10.5, 11], [10, 10.5, 11]])
    lat = np.array([[48, 48, 48], [49, 49, 49], [50, 50, 50]])
    coords = {'lon': lon, 'lat': lat}
    time = {'data': [np.array(time)], 'units': 'seconds since 1970-01-01'}
    fields = {'reflectivity': {'data': data}}
    grid_dict = {'x': x_grid, 'y': y_grid, 'z': z_grid}
    return grid.PyArtGrid(time, fields, grid_dict, coords)
