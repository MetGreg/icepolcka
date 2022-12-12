"""Module for high impact weather statistics"""
import os
import datetime as dt

import pytz
import numpy as np

from icepolcka_utils.database import algorithms, interpolations, main, models
from icepolcka_utils import utils


class Stats:
    """Statistics class

    General statistics class. Super class of all the HMC and WRF stats classes within this module.

    Args:
        cfg (dict): Configuration dictionary.
        thresh (dict): Dictionary of thresholds for each hydrometeor class. Can be either a mixing
            ratio [kg/kg] or a reflectivity [dBZ], depending on the specific ChildClass. Above this
            threshold will be considered a high impact weather event.
        height (int): Height index of data to analyze.

    Attributes:
        cfg (dict): Configuration dictionary.
        thresh (dict): Dictionary of thresholds for each hydrometeor class. Can be either a mixing
            ratio [kg/kg] or a reflectivity [dBZ], depending on the specific ChildClass. Above this
            threshold will be considered a high impact weather event.
        height (int): Height index of data to analyze.
        hms (list): Name of hydrometeors.
        file_path (str): Path to output file.
        stats (dict): Container for frequency and area statistics.


    """
    def __init__(self, cfg, thresh, height):
        self.cfg = cfg
        self.stats = {'frequency': {}, 'area': {}}
        self.hms = list(thresh.keys())
        self.thresh = thresh
        self.height = int(height)
        self._mp_to_numeric()
        self.file_path = self._make_output_folder()
        self._init_stats()

    def get_more_stats(self):
        """Calculate additional statistics

        Calculates frequency, mean, total area, and area variability from the area attribute.

        """
        for hm_name in self.stats['area']:
            for thresh in self.stats['area'][hm_name].keys():
                self.stats['frequency'][hm_name][thresh] = len(self.stats['area'][hm_name][thresh])

    def load_stats(self, file_path):
        """Load data from given file

        Args:
            file_path (str): Path to data file. Must be a .npy file that contains a dictionary with
                area and intensity data for each height and hm-class.

        """
        # Load the data
        data = np.load(file_path, allow_pickle=True)

        # Loop through all dict keys, load data, save data to area dict
        for stat, hm_name_dict in data[()].items():
            obj_stat = self.stats[stat]
            for hm_name, thresh_dict in hm_name_dict.items():
                for thresh, data_list in thresh_dict.items():
                    obj_stat[hm_name][thresh] = np.append(obj_stat[hm_name][thresh], data_list)

    def get_stats(self):
        """Calculate statistics

        Calculates the area statistics for all hydrometeor classes.

        """
        raise NotImplementedError("Implemented in child classes")

    def get_hms(self, hm_key):
        """Get hm ids/names from a hm key

        Args:
            hm_key (str): Name of hydrometeor class.

        Returns:
            list or str:
                List of hydrometeor IDs corresponding to the hydrometeor name or just the
                hydrometeor name (in case of WRF data).

        """
        raise NotImplementedError("Implemented in child classes")

    def get_hiw_pixels(self, hm_type, data, thresh, rg_data=None):
        """Get hiw pixels

        Args:
            hm_type (str or list): Either a list of hydrometeor IDs or the name of the hydrometeor
                class of interest.
            data (~numpy.ndarray): Hydrometeor classification data.
            thresh (float): Threshold for reflectivity (dBZ) or mixing ratio (kg/kg). Data below
                that threshold is put to NaN.
            rg_data (~numpy.ndarray): Regular grid data.

        Returns:
            ~numpy.ndarray:
                Array where everything below threshold and not classified as the given
                hydrometeor class was put to NaN.

        """
        raise NotImplementedError("Implemented in child classes")

    def _init_stats(self):
        self.stats['frequency'] = {}
        self.stats['area'] = {}
        for hm_name in self.hms:
            self.stats['frequency'][hm_name] = {}
            self.stats['area'][hm_name] = {}
            for thresh in self.thresh[hm_name]:
                self.stats['frequency'][hm_name][thresh] = 0
                self.stats['area'][hm_name][thresh] = []

    def _make_output_folder(self):
        parent_folder = self.cfg['output']['HIW'] + os.sep + "statistics" + os.sep \
            + str(self.height)
        start_str = dt.datetime.strftime(self.cfg['start'], "%Y-%m-%d_%H%M%S")
        end_str = dt.datetime.strftime(self.cfg['end'], "%Y-%m-%d_%H%M%S")
        output_folder = parent_folder + os.sep + self.cfg['source'] + os.sep + self.cfg['method'] \
            + os.sep
        if self.cfg['source'] == "DWD":
            output = utils.make_folder(output_folder)
        else:
            output = utils.make_folder(output_folder, mp_id=self.cfg['mp'])
        file_path = output + start_str + "_TO_" + end_str + ".npy"
        return file_path

    def _calc_stats(self, data, rg_data=None):
        for hm_name in self.hms:
            hms = self.get_hms(hm_name)
            for thresh in self.thresh[hm_name]:
                masked = self.get_hiw_pixels(hms, data, thresh, rg_data)
                area = self._calc_area(masked)
                self.stats['area'][hm_name][thresh].append(area)

    def _save_stats(self):
        stats = {'area': self.stats['area']}
        np.save(self.file_path, stats)

    def _mp_to_numeric(self):
        if self.cfg['mp'] == "None":
            self.cfg['mp'] = None
        else:
            self.cfg['mp'] = int(self.cfg['mp'])

    @staticmethod
    def _calc_area(data):
        grid_area = 400**2/1000**2
        grid_boxes = np.sum(~np.isnan(data))
        area = grid_boxes * grid_area
        return area


class HMCStats(Stats):
    """Hydrometeor classification statistics.

    Class for hydrometeor classification statistics.

    .. note::
        Most methods need the IDs of the hydrometeor classes which depend on the classification
        algorithm. That means most methods should be called from the child classes (DolanStats).

    Args:
        cfg (dict): Configuration dictionary.
        height (int): Height index of data to analyze.
        hm_ids (dict): ID of the hydrometeor classification for some classes.
        hid_var (str): Name of HID variable.

    Attributes:
        hid_var (str): Name of HID variable. Set in child classes.
        hmc_handles (list): List of HMC ResultHandles corresponding to configured time range.
            Loaded when calling get_hmc_data.
        rg_handles (list): List of RG ResultHandles corresponding to configured time range. Loaded
            when calling get_rg_data.
        hm_ids (dict): ID of the hydrometeor classification for some classes.

    """
    def __init__(self, cfg, hm_ids, hid_var, height=16):
        dbz = [5, 10, 15, 20, 25, 30, 35, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 55, 60, 65]
        thresh = {'graupel': dbz, 'hail': dbz, 'rain': dbz, 'hail_graupel': dbz}
        super().__init__(cfg, thresh, height)
        self.hm_ids = hm_ids
        self.hid_var = hid_var
        self.hmc_handles = None
        self.rg_handles = None

    def get_stats(self):
        self._get_data()
        assert len(self.rg_handles) == len(self.hmc_handles), "Handles have different length"
        for i, rg_handle in enumerate(self.rg_handles):
            time = self._assert_times(i)
            print(time)
            hmc = self.hmc_handles[i].load()
            rg_data = rg_handle.load()
            hid = hmc[self.hid_var].values
            self._calc_stats(hid, rg_data['Zhh_corr'].values)
            hmc.close()
            rg_data.close()
        self._save_stats()

    def get_hms(self, hm_key):
        if hm_key == "hail_graupel":
            ids = self.hm_ids['graupel'] + self.hm_ids['hail']
        else:
            ids = self.hm_ids[hm_key]
        return ids

    def get_hiw_pixels(self, hm_type, data, thresh, rg_data=None):
        data = data[self.height]
        rf_mask = np.load(self.cfg['masks']['RF'])
        mask = np.in1d(data, hm_type).reshape(data.shape)
        mask = mask & (rg_data[self.height] > thresh) & ~(rf_mask.astype(bool))
        masked = utils.mask_data(data, ~mask)
        return masked

    def _get_data(self):
        self.hmc_handles = main.get_handles(algorithms.HMCDataBase, self.cfg, "HMC",
                                            source=self.cfg['source'], mp_id=self.cfg['mp'],
                                            method=self.cfg['method'])
        self.rg_handles = main.get_handles(interpolations.RGDataBase, self.cfg, "RG",
                                           source=self.cfg['source'], mp_id=self.cfg['mp'],
                                           radar="Isen")

    def _assert_times(self, i):
        hmc_time = self.hmc_handles[i]['time'].replace(second=0)
        rg_time = self.rg_handles[i]['time'].replace(second=0)
        assert hmc_time == rg_time, "Hmc time does not fit to RG time"
        return self.rg_handles[i]['time'].replace(tzinfo=pytz.UTC)


class DolanStats(HMCStats):
    """Dolan hydrometeor classification statistics

    Class for statistics of hydrometeor classes that were classified with the Dolan method. Most
    functions are from the mother class 'HMCStats'. This class mainly defines hydrometeor IDs used
    by Dolan.

    Args:
        cfg (dict): Configuration dictionary.
        height (int): Height index of data to analyze.

    """
    def __init__(self, cfg, height=16):
        hm_ids = {'graupel': [7, 8], 'hail': [9, 10], 'rain': [1, 2]}
        cfg['method'] = "Dolan"
        hid_var = "HID"
        super().__init__(cfg, hm_ids, hid_var, height)


class WRFStats(Stats):
    """WRF statistics

    Used to get WRF data handles and to calculate statistics on WRF data directly. Child class of
    Stats.

    Args:
        cfg (dict): Configuration dictionary.
        height (int): Height index of data to be analyzed.

    Attributes:
        handles (list): List of data handles.

    """
    def __init__(self, cfg, height=7):
        mixing_ratio = [0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001, 0.00005, 0.00002,
                        0.00001, 0.000005, 0.000002, 0.000001]
        thresh = {'graupel': mixing_ratio, 'rain': mixing_ratio}
        cfg['method'] = "wrf"
        cfg['src'] = "MODEL"
        super().__init__(cfg, thresh, height)
        self.handles = None

    def get_stats(self):
        self.handles, _, _ = models.get_wrf_handles(self.cfg)
        for _, handle in enumerate(self.handles):
            data = handle.load()
            self._calc_stats(data)
            data.close()
        self._save_stats()

    def get_hms(self, hm_key):
        return hm_key

    def get_hiw_pixels(self, hm_type, data, thresh, rg_data=None):
        method_name = "_get_" + hm_type
        masked_data = getattr(self, method_name)(data, thresh)
        return masked_data

    def _get_hm(self, df_wrf, var, thresh):
        # Return first idx from time axis because time axis has always length 1
        data = df_wrf[var].values[0][self.height]
        masked_data = self._mask_data(data, thresh)
        return masked_data

    def _get_graupel(self, df_wrf, thresh):
        var = self._get_graupel_var()
        return self._get_hm(df_wrf, var, thresh)

    def _get_graupel_var(self):
        var = "QGRAUP"
        if self.cfg['mp'] == 50:
            var = "QIR"
        return var

    def _get_rain(self, df_wrf, thresh):
        return self._get_hm(df_wrf, "QRAIN", thresh)

    def _mask_data(self, data, thresh):
        mask = np.load(self.cfg['masks']['Distance'])
        mask = mask.astype(bool)
        mask = (data < thresh) | mask
        masked = utils.mask_data(data, mask)
        return masked
