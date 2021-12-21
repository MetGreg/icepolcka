"""Tests for handles module"""
import h5py
import os
import unittest
import datetime as dt
import numpy as np
import xarray as xr
from icepolcka_utils.handles import DataHandler, WRFDataHandler, \
    CRSIMDataHandler, DWDDataHandler, RFDataHandler, RGDataHandler, \
    TracksDataHandler, MiraDataHandler, PoldiDataHandler, ResultHandle


class DataHandlerTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_closest_rhi(self):
        self.assertRaises(NotImplementedError, DataHandler.load_data, "f")


class WRFDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = WRFDataHandler()
        self.data_path = "data" + os.sep + "wrf" + os.sep
        self.test_file1 = self.data_path + "clouds_d03_2019-07-01_140000"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file1)
        self.assertEqual(ds.attrs['MP_PHYSICS'], 8)


class CRSIMDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = CRSIMDataHandler()
        self.data_path = "data" + os.sep + "crsim" + os.sep
        self.test_file = "data" + os.sep + "crsim" + os.sep + "MP8" + os.sep \
                         + "Poldirad" + os.sep + "2019" + os.sep + "07" \
                         + os.sep + "01" + os.sep + "130000.nc"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file)
        self.assertEqual(ds.MP_PHYSICS, 8)


class RFDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = RFDataHandler()
        self.test_file = "data" + os.sep + "rf" + os.sep + "120500.nc"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file)
        self.assertEqual(len(ds['Zhh'].shape), 3)


class RGDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = RGDataHandler()
        self.test_file = "data" + os.sep + "rg" + os.sep + "MODEL" + os.sep \
                         + "130000.nc"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file)
        self.assertEqual(ds.MP_PHYSICS, 8)


class TracksDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = TracksDataHandler()
        self.test_file = "data" + os.sep + "tracks" + os.sep + "MODEL" \
                         + os.sep + "2019-06-21.pkl"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file)
        self.assertEqual(ds.MP_PHYSICS, 8)


class DWDDataHandlerTest(unittest.TestCase):
    def setUp(self):
        self.handler = DWDDataHandler()
        self.test_file = "data" + os.sep + "dwd" + os.sep\
                         + "20190621_120000.hd5"

    def tearDown(self):
        pass

    def test_load_data(self):
        ds = self.handler.load_data(self.test_file)
        site_coords = (12.101779, 48.174705, 677.77)
        self.assertEqual(ds['site_coords'], site_coords)


class MiraDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = MiraDataHandler()
        self.data_path = "data" + os.sep + "mira" + os.sep
        self.db = "data" + os.sep + "mira.db"
        self.test_new = self.data_path + "20190715_0000.mmclx"
        self.test_old = self.data_path + "20190215_0000.mmclx"
        self.test_nc = self.data_path + "20190715_0000.nc"
        self.test_site = self.data_path + "20190626_0000.mmclx"
        self.test_ppi = self.data_path + "20190917_0000.mmclx"
        self.make_datasets()

    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_load_data(self):
        data_old = self.handler.load_data(self.ds_old)
        data_new = self.handler.load_data(self.ds_new)
        data_site = self.handler.load_data(self.ds_site)

        self.assertEqual(data_old.institution, "LMU")
        self.assertEqual(data_new.institution, "LMU")
        self.assertEqual(data_site.site_coords, (11.57355, 48.148021, 541))
        self.assertRaises(AssertionError, self.handler.load_data,
                          self.ds_missing)

    def test_get_site_coords(self):
        ds_old = xr.open_dataset(self.test_old)
        ds_new = xr.open_dataset(self.test_new)
        ds_nc = xr.open_dataset(self.test_nc)
        lon1, lat1, alt1 = self.handler.get_site_coords(ds_old)
        lon2, lat2, alt2 = self.handler.get_site_coords(ds_new)
        lon3, lat3, alt3 = self.handler.get_site_coords(ds_nc)
        self.assertAlmostEqual(lon1, 11.573, places=2)
        self.assertAlmostEqual(lon2, 11.573, places=2)
        self.assertAlmostEqual(lon3, 11.573, places=2)
        self.assertAlmostEqual(lat1, 48.148, places=2)
        self.assertAlmostEqual(lat2, 48.148, places=2)
        self.assertAlmostEqual(lat3, 48.148, places=2)
        self.assertEqual(alt1, 541)
        self.assertEqual(alt2, 541)
        self.assertEqual(alt3, 541)

    def test_find_rhi_sweeps(self):
        data_old = self.handler.load_data(self.ds_old)
        data_new = self.handler.load_data(self.ds_new)
        sweeps_old = self.handler.find_rhi_sweeps(data_old)
        sweeps_new = self.handler.find_rhi_sweeps(data_new)
        self.assertEqual(sweeps_old[0], slice(341, 507, None))
        self.assertEqual(sweeps_new[0], slice(2, 166, None))

    def make_datasets(self):
        self.ds_old = {'mmclx_file': self.test_old, 'nc_file': None}
        self.ds_new = {'mmclx_file': self.test_new, 'nc_file': self.test_nc}
        self.ds_site = {'mmclx_file': self.test_site, 'nc_file': None}
        self.ds_missing = {'mmclx_file': "/random/path/file.mmclx",
                           'nc_file': None}
        self.ds_ppi = {'mmclx_file': self.test_ppi, 'nc_file': None}


class PoldiDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.handler = PoldiDataHandler()
        self.test_file = "data" + os.sep + "poldi" + os.sep + "correct_data" \
                         + os.sep + "overview.hdf5"
        self.test_file2 = "data" + os.sep + "poldi" + os.sep + "correct_data" \
                          + os.sep + "wrong_data" + os.sep + "ST009" + os.sep \
                          + "no_task.hdf5"
        self.test_file3 = "data" + os.sep + "poldi" + os.sep + "correct_data" \
                          + os.sep + "SRHI.hdf5"
        self.error_file = "data" + os.sep + "poldi" + os.sep + "error_data" \
                          + os.sep + "wrong_task.hdf5"

    def tearDown(self):
        pass

    def test_load_data(self):
        data = self.handler.load_data(self.test_file)
        data2 = self.handler.load_data(self.test_file2)
        data3 = self.handler.load_data(self.test_file3, scan=1)
        self.assertEqual(data.institution, "DLR")
        self.assertEqual(data2.task, "RHI")
        self.assertEqual(data3.task, "RHI")
        self.assertRaises(AssertionError, self.handler.load_data,
                          self.error_file)

    def test_split_poldi_az(self):
        string1 = "350.1:350.5,350.5:358.5"
        string2 = "359:1,1:10"
        string3 = "-0.2:-0.1,1:2"
        l1 = self.handler.split_poldi_az(string1)
        l2 = self.handler.split_poldi_az(string2)
        l3 = self.handler.split_poldi_az(string3)
        np.testing.assert_array_equal(l1, np.array([350.3, 354.5]))
        np.testing.assert_array_equal(l2, np.array([0, 5.5]))
        np.testing.assert_array_equal(l3, np.array([359.85, 1.5]))

    def test_gain_to_data(self):
        pd = h5py.File(self.test_file)
        pd_data = pd['dataset1']['data1']
        reflect = self.handler.gain_to_data(pd_data)
        self.assertAlmostEqual(reflect[0, 0], -15.67, places=2)

    def test_split_poldi_elv(self):
        string1 = "89.1:89.5,89.7:89.9"
        string2 = "-0.5:-0.2,-0.1:0.2"
        l1 = self.handler.split_poldi_elv(string1)
        l2 = self.handler.split_poldi_elv(string2)
        np.testing.assert_array_almost_equal(l1, np.array([89.3, 89.8]))
        np.testing.assert_array_almost_equal(l2, np.array([-0.35, 0.05]))

    def test_get_correct_datetime(self):
        time_start = dt.datetime(2019, 6, 14, 23, 58)
        time_end1 = dt.datetime(2019, 6, 14, 23, 59)
        time_end2 = dt.datetime(2019, 6, 15, 0, 0)
        time_array1 = [dt.datetime(1900, 1, 1, 23, 58),
                       dt.datetime(1900, 1, 1, 23, 59)]
        time_array2 = [dt.datetime(1900, 1, 1, 23, 58),
                       dt.datetime(1900, 1, 1, 0, 0)]
        times1 = self.handler.get_correct_datetime(time_array1, time_start,
                                                   time_end1)
        times2 = self.handler.get_correct_datetime(time_array2, time_start,
                                                   time_end2)
        exp1 = np.array([dt.datetime(2019, 6, 14, 23, 58),
                         dt.datetime(2019, 6, 14, 23, 59)])
        exp2 = np.array([dt.datetime(2019, 6, 14, 23, 58),
                         dt.datetime(2019, 6, 15, 0, 0)])
        np.testing.assert_array_equal(times1, exp1)
        np.testing.assert_array_equal(times2, exp2)


class ResultHandleTest(unittest.TestCase):
    def setUp(self):
        self.test_file = "data" + os.sep + "poldi" + os.sep + "correct_data" \
                         + os.sep + "overview.hdf5"
        self.missing_file = "random_file"

    def tearDown(self):
        pass

    def test_load(self):
        attrs = {'task': "PPI"}
        data_handler = PoldiDataHandler()

        def load_func():
            return data_handler.load_data(self.test_file)

        def load_func2():
            return data_handler.load_data(self.missing_file)

        handle = ResultHandle(attrs, load_func)
        handle2 = ResultHandle(attrs, load_func2)
        ds = handle.load()
        self.assertEqual(handle['task'], "PPI")
        self.assertEqual(ds.task, "PPI")
        self.assertRaises(OSError, handle2.load)


if __name__ == "__main__":
    unittest.main()
