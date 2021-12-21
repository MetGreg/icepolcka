"""Tests for data base module"""
import os
import unittest
import datetime as dt
from shutil import copyfile

from icepolcka_utils.data_base import create_session, create_db, get_closest,\
    Datafile, Domain, MPScheme, Dataset, Radar, CRSIMData, PPIData, RHIData, \
    SRHIData, DWDData, DataBase, WRFDataBase, CRSIMDataBase, RFDataBase, \
    RGDataBase, TracksDataBase, RadarDataBase, DWDDataBase, MiraDataBase, \
    PoldiDataBase


class FunctionTest(unittest.TestCase):

    def setUp(self):
        self.db_path = "data" + os.sep + "test.db"
        self.crsim_path = "data" + os.sep + "crsim" + os.sep

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_session(self):
        s = create_session(self.db_path)
        self.assertTrue(s is not None)

    def test_create_db(self):
        s = create_db(self.db_path)
        q = s.query(Radar).all()
        self.assertTrue(len(q), 3)  # 3 radars (DWD, Mira-35, Poldirad)

    def test_get_closest(self):
        time_lesser = dt.datetime(2019, 7, 1, 12, 48)
        time_greater = dt.datetime(2019, 7, 1, 13, 5)
        exp_time = dt.datetime(2019, 7, 1, 13)
        with CRSIMDataBase(self.crsim_path, self.db_path):
            pass
        s = create_session(self.db_path)
        query = s.query(CRSIMData)
        closest_lesser = get_closest(query, CRSIMData.time, time_lesser)
        closest_greater = get_closest(query, CRSIMData.time, time_greater)
        self.assertEqual(closest_lesser.time, exp_time)
        self.assertEqual(closest_greater.time, exp_time)


class DataBaseTest(unittest.TestCase):

    def setUp(self):
        self.data_base = DataBase()

    def tearDown(self):
        pass

    def test_get_data(self):
        self.assertRaises(NotImplementedError, self.data_base.get_data,
                          dt.datetime.now(), dt.datetime.now())

    def test_closest_get_data(self):
        self.assertRaises(NotImplementedError, self.data_base.get_closest_data,
                          dt.datetime.now())

    def test_latest_get_data(self):
        self.assertRaises(NotImplementedError, self.data_base.get_latest_data)

    def test_update_db(self):
        self.assertRaises(NotImplementedError, self.data_base.update_db)


class WRFDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.wrf_path = "data" + os.sep + "wrf" + os.sep
        self.wrf_path2 = "data" + os.sep + "wrf2" + os.sep
        self.wrf_db = "data" + os.sep + "wrf.db"
        self.wrf_db2 = "data" + os.sep + "wrf2.db"
        self.wrf_db3 = "data" + os.sep + "wrf3.db"
        self.wrf_file = "data" + os.sep + "wrf" + os.sep \
                        + "clouds_d03_2019-07-01_140000"
        self.wrf_file2 = "data" + os.sep + "wrf2" + os.sep \
                         + "clouds_d03_2019-07-01_140000"
        self.wrfout_file = "data" + os.sep + "wrf" + os.sep \
                           + "wrfout_d03_2019-07-01_140000"
        self.wrfout_file2 = "data" + os.sep + "wrf2" + os.sep \
                            + "wrfout_d03_2019-07-01_140000"
        self.duplicate = "data" + os.sep + "wrf" + os.sep \
                         + "clouds_d03_2019-07-01_140001"

    def tearDown(self):
        if os.path.exists(self.wrf_db):
            os.remove(self.wrf_db)
        if os.path.exists(self.wrf_db2):
            os.remove(self.wrf_db2)
        if os.path.exists(self.wrf_db3):
            os.remove(self.wrf_db3)
        if os.path.exists(self.wrfout_file2):
            os.remove(self.wrfout_file2)
        if os.path.exists(self.wrf_file2):
            os.remove(self.wrf_file2)
        if os.path.exists(self.duplicate):
            os.remove(self.duplicate)

    def test_get_data(self):
        start = dt.datetime(2019, 7, 1, 12)
        end = dt.datetime(2019, 7, 1, 14)
        with WRFDataBase(self.wrf_path, self.wrf_db) as wrf_db:
            handle = wrf_db.get_data(start, end, mp_id=8, domain="Munich")
            handle2 = wrf_db.get_data(start, start, mp_id=10, domain="Europe")
        data = handle[0]['clouds'].load()
        self.assertEqual(data.mp_id, 8)
        self.assertEqual(handle[0]['clouds']['mp_id'], 8)
        self.assertEqual(len(handle2), 0)

    def test_get_closest_data(self):
        close_start = dt.datetime(2019, 7, 1, 15, 0, 0)
        close_end = dt.datetime(2019, 7, 1, 15, 5, 0)
        exp_time = dt.datetime(2019, 7, 1, 15, 0, 0)
        with WRFDataBase(self.wrf_path, self.wrf_db) as wrf_db:
            handle1 = wrf_db.get_closest_data(close_start)
            handle2 = wrf_db.get_closest_data(close_end, mp_id=8,
                                              domain="Munich")
        data = handle1['clouds'].load()
        data2 = handle2['clouds'].load()
        self.assertEqual(data.start_time, exp_time)
        self.assertEqual(data2.start_time, exp_time)

    def test_get_latest_data(self):
        exp_time = dt.datetime(2019, 7, 1, 15, 0, 0)
        with WRFDataBase(self.wrf_path, self.wrf_db) as wrf_db:
            handle1 = wrf_db.get_latest_data()[0]
        data = handle1['clouds'].load()
        self.assertEqual(data.start_time, exp_time)

    def test_update_db(self):
        s = create_db(self.wrf_db)
        check_time = dt.datetime(2019, 1, 1)
        start = dt.datetime(2019, 7, 1, 14)
        end = dt.datetime(2019, 7, 1, 15)

        self.update_and_test(self.wrf_path, self.wrf_db, True, start, end,
                             "clouds")

        # Repeat to cover testing of pre loaded files
        self.update_and_test(self.wrf_path, self.wrf_db, False, start, end,
                             "clouds")

        # Redo to test recheck=True
        wrf_file = s.query(Datafile).filter(
            Datafile.filename == self.wrf_file
            ).one()
        wrf_file.last_checked = check_time
        s.commit()
        self.update_and_test(self.wrf_path, self.wrf_db, True, start, end,
                             "clouds")

        # Test reverse loading (First wrfout, then clouds)
        copyfile(self.wrfout_file, self.wrfout_file2)
        self.update_and_test(self.wrf_path2, self.wrf_db2, False, start, end,
                             "wrfout")

        # Now copy the new mmclx file to destination and repeat update of db
        copyfile(self.wrf_file, self.wrf_file2)
        self.update_and_test(self.wrf_path2, self.wrf_db2, False, start, end,
                             "wrfout")

        # Test duplicates
        with WRFDataBase(self.wrf_path, self.wrf_db, recheck=False) as wrf_db:
            handle = wrf_db.get_data(start, end)[0]['clouds']
            model = wrf_db.model
        s = create_db(self.wrf_db3)
        mp = s.query(MPScheme).filter_by(id=handle['mp_id']).one()
        domain = s.query(Domain).filter_by(name=handle['domain'].name).one()
        dataset = Dataset(start_time=handle['start_time'],
                          end_time=handle['end_time'], mp=mp, domain=domain,
                          model=model)
        dataset2 = Dataset(start_time=handle['start_time'],
                           end_time=handle['end_time'], mp=mp, domain=domain,
                           model=model)
        s.add(domain)
        s.add(mp)
        s.add(dataset)
        s.add(dataset2)
        s.commit()
        with WRFDataBase(self.wrf_path, self.wrf_db3,
                         update=False, recheck=False) as wrf_db:
            self.assertRaises(AssertionError, wrf_db.update_db, False)

    def update_and_test(self, path, db, recheck, start, end, file_type):
        with WRFDataBase(path, db, recheck=recheck) as wrf_db:
            handle = wrf_db.get_data(start, end)
        self.assertEqual(handle[0][file_type]['start_time'], start)


class CRSIMDataBaseTest(unittest.TestCase):
    def setUp(self):
        self.crsim_path = "data" + os.sep + "crsim" + os.sep
        self.crsim_db = "data" + os.sep + "crsim.db"
        self.crsim_file = "data" + os.sep + "crsim" + os.sep + "MP8" + os.sep \
                          + "Poldirad" + os.sep + "2019" + os.sep + "07" \
                          + os.sep + "01" + os.sep + "130000.nc"

    def tearDown(self):
        if os.path.exists(self.crsim_db):
            os.remove(self.crsim_db)

    def test_get_data(self):
        with CRSIMDataBase(self.crsim_path, self.crsim_db) as crsim_db:
            start = dt.datetime(2019, 7, 1, 12)
            end = dt.datetime(2019, 7, 1, 14)
            handle = crsim_db.get_data(start, end, mp_id=28, radar="Poldirad",
                                       hm="all")[0]
        data = handle.load()
        self.assertEqual(data.mp, 28)
        self.assertEqual(handle['mp'], 28)

    def test_get_closest_data(self):
        time = dt.datetime(2019, 7, 1, 13, minute=58)
        exp_time = dt.datetime(2019, 7, 1, 14)
        exp_time2 = dt.datetime(2019, 7, 1, 13)
        with CRSIMDataBase(self.crsim_path, self.crsim_db) as crsim_db:
            handle = crsim_db.get_closest_data(time)
            handle2 = crsim_db.get_closest_data(time, mp_id=8, radar="Poldirad")
        data = handle.load()
        data2 = handle2.load()
        data_time = dt.datetime.strptime(str(data.time.values),
                                         "%Y-%m-%dT%H:%M:%S.%f000")
        data2_time = dt.datetime.strptime(str(data2.time.values),
                                          "%Y-%m-%dT%H:%M:%S.%f000")
        self.assertEqual(data.mp, 28)
        self.assertEqual(data_time, exp_time)
        self.assertEqual(data2.mp, 8)
        self.assertEqual(data2_time, exp_time2)

    def test_get_latest_data(self):
        exp_time = dt.datetime(2019, 7, 1, 14)
        with CRSIMDataBase(self.crsim_path, self.crsim_db) as crsim_db:
            handle = crsim_db.get_latest_data()[0]
        data = handle.load()
        data_time = dt.datetime.strptime(str(data.time.values),
                                         "%Y-%m-%dT%H:%M:%S.%f000")
        self.assertEqual(data.mp, 28)
        self.assertEqual(data_time, exp_time)

    def test_update_db(self):
        s = create_db(self.crsim_db)
        check_time = dt.datetime(2019, 1, 1)
        start = dt.datetime(2019, 7, 1, 14)
        end = dt.datetime(2019, 7, 1, 15)

        self.update_and_test(self.crsim_path, self.crsim_db, True, start, end)

        # Repeat to cover testing of pre loaded files
        self.update_and_test(self.crsim_path, self.crsim_db, False, start, end)

        # Redo to test recheck=True
        crsim_file = s.query(Datafile).filter(
            Datafile.filename == self.crsim_file
            ).one()
        crsim_file.last_checked = check_time
        s.commit()
        self.update_and_test(self.crsim_path, self.crsim_db, True, start, end)

    def update_and_test(self, path, db, recheck, start, end):
        with CRSIMDataBase(path, db, recheck=recheck) as crsim_db:
            handle = crsim_db.get_data(start, end)[-1]
        self.assertEqual(handle['mp'], 28)


class RadarFilterDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.rf_path = "data" + os.sep + "rf" + os.sep
        self.rf_db = "data" + os.sep + "rf.db"
        self.rf_file = "data" + os.sep + "rf" + os.sep + "120500.nc"

    def tearDown(self):
        if os.path.exists(self.rf_db):
            os.remove(self.rf_db)

    def test_get_data(self):
        start = dt.datetime(2019, 7, 8, 12)
        end = dt.datetime(2019, 7, 8, 13)
        with RFDataBase(self.rf_path, self.rf_db) as rf_db:
            handle = rf_db.get_data(start, end, mp_id=10, radar="Poldirad")[0]
        data = handle.load()
        self.assertEqual(len(data['Zhh'].shape), 3)
        self.assertEqual(handle['mp'], 10)

    def test_get_closest_data(self):
        time = dt.datetime(2019, 7, 8, 13, minute=58)
        exp_time = dt.datetime(2019, 7, 8, 12, minute=5)
        with RFDataBase(self.rf_path, self.rf_db) as rf_db:
            handle = rf_db.get_closest_data(time, mp_id=10, radar="Poldirad")
        data = handle.load()
        self.assertEqual(len(data['Zhh'].shape), 3)
        self.assertEqual(handle['time'], exp_time)

    def test_get_latest_data(self):
        exp_time = dt.datetime(2019, 7, 8, 12, minute=5)
        with RFDataBase(self.rf_path, self.rf_db) as rf_db:
            handle = rf_db.get_latest_data()[0]
        data = handle.load()
        self.assertEqual(len(data['Zhh'].shape), 3)
        self.assertEqual(handle['time'], exp_time)

    def test_update_db(self):
        s = create_db(self.rf_db)
        check_time = dt.datetime(2019, 1, 1)
        start = dt.datetime(2019, 7, 8, 12)
        end = dt.datetime(2019, 7, 8, 14)

        self.update_and_test(self.rf_path, self.rf_db, True, start, end)

        # Repeat to cover testing of pre loaded files
        self.update_and_test(self.rf_path, self.rf_db, True, start, end)

        # Redo to test recheck=False
        self.update_and_test(self.rf_path, self.rf_db, False, start, end)

        # Redo to test recheck=True
        rf_file = s.query(Datafile).filter(
            Datafile.filename == self.rf_file
            ).one()
        rf_file.last_checked = check_time
        s.commit()
        self.update_and_test(self.rf_path, self.rf_db, True, start, end)

    def update_and_test(self, path, db, recheck, start, end):
        with RFDataBase(path, db, recheck=recheck) as rf_db:
            handle = rf_db.get_data(start, end)[-1]
        self.assertEqual(handle['mp'], 10)


class RGDataBaseTest(unittest.TestCase):
    def setUp(self):
        self.grid_path = "data" + os.sep + "rg" + os.sep
        self.grid_db = "data" + os.sep + "rg.db"
        self.grid_file = "data" + os.sep + "rg" + os.sep + "MODEL" + os.sep \
                         + "130000.nc"

    def tearDown(self):
        if os.path.exists(self.grid_db):
            os.remove(self.grid_db)

    def test_get_data(self):
        start = dt.datetime(2019, 7, 1, 12)
        end = dt.datetime(2020, 7, 1, 14)
        with RGDataBase(self.grid_path, self.grid_db) as grid_db:
            handle = grid_db.get_data(start, end, source="MODEL", mp_id=8,
                                      radar="Poldirad")[0]
        data = handle.load()
        self.assertEqual(data.mp, 8)
        self.assertEqual(handle['mp'], 8)

    def test_get_closest_data(self):
        time = dt.datetime(2019, 7, 1, 12, 58)
        exp_time = dt.datetime(2019, 7, 1, 13, 0, 0)
        with RGDataBase(self.grid_path, self.grid_db) as grid_db:
            handle = grid_db.get_closest_data(time, mp_id=8, radar="Poldirad")
        data = handle.load()
        self.assertEqual(data.mp, 8)
        self.assertEqual(data.time, exp_time)

    def test_get_latest_data(self):
        with RGDataBase(self.grid_path, self.grid_db) as grid_db:
            handle = grid_db.get_latest_data()[0]
        data = handle.load()
        self.assertEqual(data.mp, 8)

    def test_update_db(self):
        s = create_db(self.grid_db)
        check_time = dt.datetime(2019, 1, 1)
        start = dt.datetime(2019, 7, 1, 12)
        end = dt.datetime(2020, 7, 1, 14)

        self.update_and_test(self.grid_path, self.grid_db, True, start, end)

        # Repeat to cover testing of pre loaded files
        self.update_and_test(self.grid_path, self.grid_db, False, start, end)

        # Redo to test recheck=True
        self.update_and_test(self.grid_path, self.grid_db, True, start, end)

        # Redo with check timestamp of file changed to force redo
        grid_file = s.query(Datafile).filter(
            Datafile.filename == self.grid_file
            ).one()
        grid_file.last_checked = check_time
        s.commit()
        self.update_and_test(self.grid_path, self.grid_db, True, start, end)

    def update_and_test(self, path, db, recheck, start, end):
        with RGDataBase(path, db, recheck=recheck) as grid_db:
            handle = grid_db.get_data(start, end)[-1]
        self.assertEqual(handle['mp'], 8)


class TracksDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.tracks_path = "data" + os.sep + "tracks" + os.sep
        self.tracks_db = "data" + os.sep + "tracks.db"
        self.test_file = "data" + os.sep + "tracks" + os.sep + "MODEL" \
                         + os.sep + "2019-06-21.pkl"

    def tearDown(self):
        if os.path.exists(self.tracks_db):
            os.remove(self.tracks_db)

    def test_get_data(self):
        start = dt.datetime(2019, 6, 21)
        end = dt.datetime(2019, 6, 22)
        with TracksDataBase(self.tracks_path, self.tracks_db) as tracks_db:
            handle = tracks_db.get_data(start, end, source="MODEL", mp_id=8,
                                        radar="Isen")[0]
        self.assertEqual(handle['mp'], 8)

    def test_get_closest_data(self):
        time = dt.datetime(2019, 6, 22)
        exp_date = dt.datetime(2019, 6, 21)
        with TracksDataBase(self.tracks_path, self.tracks_db) as tracks_db:
            handle = tracks_db.get_closest_data(time, mp_id=8, radar="Isen")
        self.assertEqual(handle['date'], exp_date)

    def test_get_latest_data(self):
        exp_date = dt.datetime(2019, 7, 1)
        with TracksDataBase(self.tracks_path, self.tracks_db) as tracks_db:
            handle = tracks_db.get_latest_data()[0]
        self.assertEqual(handle['date'], exp_date)

    def test_update_db(self):
        session = create_db(self.tracks_db)
        check_time = dt.datetime(2019, 1, 1)
        start = dt.datetime(2019, 6, 21)
        end = dt.datetime(2019, 6, 22)

        self.update_and_test(self.tracks_path, self.tracks_db, True, start, end)

        # Repeat to cover testing of pre loaded files
        self.update_and_test(self.tracks_path, self.tracks_db, True, start, end)

        # Redo to test recheck=False
        self.update_and_test(self.tracks_path, self.tracks_db, False, start,
                             end)

        # Redo to test recheck=True
        tracks_file = session.query(Datafile).filter(
            Datafile.filename == self.test_file
            ).one()
        tracks_file.last_checked = check_time
        session.commit()
        self.update_and_test(self.tracks_path, self.tracks_db, True, start, end)

    def update_and_test(self, path, db, recheck, start, end):
        with TracksDataBase(path, db, recheck=recheck) as tracks_db:
            handle = tracks_db.get_data(start, end)[-1]
        self.assertEqual(handle['mp'], 8)


class RadarDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.radar_data = RadarDataBase()

    def tearDown(self):
        pass

    def test_get_closest_rhi(self):
        self.assertRaises(NotImplementedError, self.radar_data.get_closest_rhi,
                          dt.datetime.now())

    def test_get_closest_ppi(self):
        self.assertRaises(NotImplementedError, self.radar_data.get_closest_ppi,
                          dt.datetime.now())

    def test_get_data(self):
        self.assertRaises(NotImplementedError, self.radar_data.get_data,
                          dt.datetime.now(), dt.datetime.now())

    def test_closest_get_data(self):
        self.assertRaises(NotImplementedError, self.radar_data.get_closest_data,
                          dt.datetime.now())

    def test_latest_get_data(self):
        self.assertRaises(NotImplementedError, self.radar_data.get_latest_data)

    def test_update_db(self):
        self.assertRaises(NotImplementedError, self.radar_data.update_db)


class DWDDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.dwd_path = "data" + os.sep + "dwd" + os.sep
        self.dwd_db = "data" + os.sep + "dwd.db"
        self.test_file = "data" + os.sep + "dwd" + os.sep \
                         + "20190621_120000.hd5"

    def tearDown(self):
        if os.path.exists(self.dwd_db):
            os.remove(self.dwd_db)

    def test_get_closest_rhi(self):
        with DWDDataBase(self.dwd_path, self.dwd_db) as dwd_db:
            self.assertRaises(NotImplementedError, dwd_db.get_closest_rhi,
                              dt.datetime.now())

    def test_get_closest_ppi(self):
        with DWDDataBase(self.dwd_path, self.dwd_db) as dwd_db:
            self.assertRaises(NotImplementedError, dwd_db.get_closest_ppi,
                              dt.datetime.now())

    def test_get_data(self):
        start = dt.datetime(2019, 6, 21)
        end = dt.datetime(2019, 6, 22)
        with DWDDataBase(self.dwd_path, self.dwd_db) as dwd_db:
            handle = dwd_db.get_data(start, end)[0]
        exp_time = dt.datetime(2019, 6, 21, 12, 0, 35)
        self.assertEqual(handle['time'], exp_time)

    def test_get_closest_data(self):
        time = dt.datetime(2019, 6, 22)
        with DWDDataBase(self.dwd_path, self.dwd_db) as dwd_db:
            handle = dwd_db.get_closest_data(time)
        exp_time = dt.datetime(2019, 6, 21, 12, 0, 35)
        self.assertEqual(handle['time'], exp_time)

    def test_get_latest_data(self):
        with DWDDataBase(self.dwd_path, self.dwd_db) as dwd_db:
            handle = dwd_db.get_latest_data()[0]
        exp_time = dt.datetime(2019, 6, 21, 12, 0, 35)
        self.assertEqual(handle['time'], exp_time)

    def test_update_db(self):
        s = create_db(self.dwd_db)
        check_time = dt.datetime(2019, 1, 1)
        self.update_and_count(self.dwd_path, self.dwd_db, True)

        # Repeat to test recheck=False
        self.update_and_count(self.dwd_path, self.dwd_db, False)

        # Repeat to cover testing of pre loaded files
        self.update_and_count(self.dwd_path, self.dwd_db, True)

        # Redo to test recheck=True
        dwd_file = s.query(Datafile).filter(
            Datafile.filename == self.test_file
            ).one()
        dwd_file.last_checked = check_time
        s.commit()
        self.update_and_count(self.dwd_path, self.dwd_db, True)

    def update_and_count(self, path, db, recheck):
        with DWDDataBase(path, db) as dwd_db:
            dwd_db.update_db(recheck=recheck)
        s = create_session(self.dwd_db)
        q = s.query(DWDData).all()
        self.assertEqual(len(q), 1)


class MiraDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.mira_path = "data" + os.sep + "mira" + os.sep
        self.mira_path2 = "data" + os.sep + "mira2" + os.sep
        self.mira_db = "data" + os.sep + "mira.db"
        self.mira_db2 = "data" + os.sep + "mira" + os.sep + "mira2.db"
        self.mira_db3 = "data" + os.sep + "mira3.db"
        self.mira_db4 = "data" + os.sep + "mira4.db"
        self.mira_nc = self.mira_path + "20190715_0000.nc"  # 1 RHI scan
        self.mira_mmclx = self.mira_path + "20190715_0000.mmclx"  # Same scan
        self.mira_ppi = self.mira_path + "20190917_0000.mmclx"  # 2 PPI scans

    def tearDown(self):
        if os.path.exists(self.mira_db):
            os.remove(self.mira_db)
        if os.path.exists(self.mira_db2):
            os.remove(self.mira_db2)
        if os.path.exists(self.mira_db3):
            os.remove(self.mira_db3)
        if os.path.exists(self.mira_db4):
            os.remove(self.mira_db4)
        for f in os.listdir(self.mira_path2):
            os.remove(self.mira_path2 + os.sep + f)

    def test_get_rhis(self):
        start = dt.datetime(2019, 2, 15)
        end = dt.datetime.utcnow()
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            scan_handles = mira_db.get_rhis(start, end)
        scan_data = scan_handles[1].load()
        scan_time = dt.datetime.strptime(str(scan_data.times.values[0]),
                                         "%Y-%m-%dT%H:%M:%S.%f000")
        exp_time = dt.datetime(2019, 7, 15, 9, 8, 36)
        self.assertEqual(len(scan_handles), 2)
        self.assertEqual(scan_time, exp_time)

    def test_get_closest_rhi(self):
        close = dt.datetime(2019, 7, 15, 9, 8, 41)
        exp_time = dt.datetime(2019, 7, 15, 9, 8, 36)
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            handle = mira_db.get_closest_rhi(close)
        self.assertEqual(handle['start_time'], exp_time)

    def test_get_closest_ppi(self):
        close = dt.datetime(2019, 9, 9, 17, 8, 41)
        exp_time = dt.datetime(2019, 9, 17, 14, 0, 58)
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            handle = mira_db.get_closest_ppi(close)
        self.assertEqual(handle['start_time'], exp_time)

    def test_get_data(self):
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            self.assertRaises(NotImplementedError, mira_db.get_data,
                              dt.datetime.now(), dt.datetime.now())

    def test_get_closest_data(self):
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            self.assertRaises(NotImplementedError, mira_db.get_closest_data,
                              dt.datetime.now())

    def test_get_latest_data(self):
        with MiraDataBase(self.mira_path, self.mira_db) as mira_db:
            self.assertRaises(NotImplementedError, mira_db.get_latest_data)

    def test_update_db(self):
        s = create_db(self.mira_db)
        check_time = dt.datetime(2019, 1, 1)
        self.update_and_count(self.mira_path, self.mira_db, True)

        # Test recheck=False
        self.update_and_count(self.mira_path, self.mira_db, False)

        # Redo to test recheck=True
        mmclx_file = s.query(Datafile).filter(
            Datafile.filename == self.mira_ppi
            ).one()
        mmclx_file.last_checked = check_time
        s.commit()
        self.update_and_count(self.mira_path, self.mira_db, True)

        # Test .db file in the same folder
        self.update_and_count(self.mira_path, self.mira_db, True)

        # Test duplicates
        with MiraDataBase(self.mira_path, self.mira_db, recheck=False) as \
                mira_db:
            handle = mira_db.get_closest_rhi(dt.datetime.now())
        s = create_db(self.mira_db3)
        dataset = Dataset(start_time=handle['start_time'],
                          end_time=handle['end_time'])
        dataset2 = Dataset(start_time=handle['start_time'],
                           end_time=handle['end_time'])
        s.add(dataset)
        s.add(dataset2)
        s.commit()
        with MiraDataBase(self.mira_path, self.mira_db3,
                          update=False, recheck=False) as mira_db:
            self.assertRaises(AssertionError, mira_db.update_db, False)

        # Test reverse order (First mmclx then nc)
        copyfile(self.mira_mmclx, self.mira_path2 + os.sep + "file.mmclx")
        with MiraDataBase(self.mira_path2, self.mira_db,
                          recheck=False) as mira_db:
            copyfile(self.mira_nc, self.mira_path2 + os.sep + "file.nc")
            mira_db.update_db()
        self.update_and_count(self.mira_path2, self.mira_db4, False, True,
                              scans=1)

    def update_and_count(self, path, db, recheck, update=True, scans=4):
        with MiraDataBase(path, db, update=update, recheck=recheck) as mira_db:
            mira_db.update_db()
        s = create_session(db)
        q1 = s.query(PPIData).all()
        q2 = s.query(RHIData).all()
        self.assertEqual(len(q1 + q2), scans)


class PoldiDataBaseTest(unittest.TestCase):

    def setUp(self):
        self.poldi_path = "data" + os.sep + "poldi" + os.sep + "correct_data" \
                          + os.sep
        self.poldi_db = "data" + os.sep + "poldi.db"
        self.poldi_db2 = "data" + os.sep + "poldi" + os.sep + "poldi2.db"
        self.poldi_db3 = "data" + os.sep + "poldi3.db"
        self.poldi_db4 = "data" + os.sep + "poldi4.db"
        self.ppi_file = self.poldi_path + "overview.hdf5"
        self.rhi_file = self.poldi_path + "RHI.hdf5"
        self.srhi_file = self.poldi_path + "RHI.hdf5"

    def tearDown(self):
        if os.path.exists(self.poldi_db):
            os.remove(self.poldi_db)
        if os.path.exists(self.poldi_db2):
            os.remove(self.poldi_db2)
        if os.path.exists(self.poldi_db3):
            os.remove(self.poldi_db3)
        if os.path.exists(self.poldi_db4):
            os.remove(self.poldi_db4)

    def test_get_closest_rhi(self):
        close = dt.datetime(2019, 6, 21, 10, 38, 46)
        exp_time = dt.datetime(2019, 6, 21, 10, 38, 48)
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            handle = poldi_db.get_closest_rhi(close)
        self.assertEqual(handle['start_time'], exp_time)

    def test_get_closest_ppi(self):
        close = dt.datetime(2019, 6, 21, 10, 38, 46)
        exp_time = dt.datetime(2019, 1, 30, 12, 0, 46)
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            handle = poldi_db.get_closest_ppi(close)
        self.assertEqual(handle['start_time'], exp_time)

    def test_get_closest_srhi(self):
        close = dt.datetime(2019, 7, 1, 12, 46, 40)
        exp_time = dt.datetime(2019, 7, 1, 12, 46, 22)
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            handle = poldi_db.get_closest_srhi(close)
        self.assertEqual(handle[0]['start_time'], exp_time)

    def test_get_data(self):
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            self.assertRaises(NotImplementedError, poldi_db.get_data,
                              dt.datetime.now(), dt.datetime.now())

    def test_get_closest_data(self):
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            self.assertRaises(NotImplementedError, poldi_db.get_closest_data,
                              dt.datetime.now())

    def test_get_latest_data(self):
        with PoldiDataBase(self.poldi_path, self.poldi_db) as poldi_db:
            self.assertRaises(NotImplementedError, poldi_db.get_latest_data)

    def test_update_db(self):
        s = create_db(self.poldi_db)
        check_time = dt.datetime(2019, 1, 1)
        self.update_and_count(self.poldi_path, self.poldi_db, True)

        # Test recheck=False
        self.update_and_count(self.poldi_path, self.poldi_db, False)

        # Redo to test recheck=True
        ppi_file = s.query(Datafile).filter(
            Datafile.filename == self.ppi_file
            ).one()
        rhi_file = s.query(Datafile).filter(
            Datafile.filename == self.rhi_file
            ).one()
        ppi_file.last_checked = check_time
        rhi_file.last_checked = check_time
        s.commit()
        self.update_and_count(self.poldi_path, self.poldi_db, True)

        # Test with .db file in same folder as data
        self.update_and_count(self.poldi_path, self.poldi_db2, True)

        # Redo test with .db file in same folder as data to test update
        self.update_and_count(self.poldi_path, self.poldi_db2, True)

        # Test RHI duplicates
        with PoldiDataBase(self.poldi_path, self.poldi_db,
                           recheck=False) as poldi_db:
            handle = poldi_db.get_closest_rhi(dt.datetime.now())
        s = create_db(self.poldi_db3)
        radar = s.query(Radar).filter_by(name="Poldirad").one()
        scan = RHIData(radar=radar, start_time=handle['start_time'])
        scan2 = RHIData(radar=radar, start_time=handle['start_time'])
        s.add(scan)
        s.add(scan2)
        s.commit()
        with PoldiDataBase(self.poldi_path, self.poldi_db3,
                           update=False, recheck=False) as poldi_db:
            self.assertRaises(AssertionError, poldi_db.update_db, False)

        # Test SRHI duplicates
        with PoldiDataBase(self.poldi_path, self.poldi_db,
                           recheck=False) as poldi_db:
            handle = poldi_db.get_closest_srhi(dt.datetime.now())[0]
        s = create_db(self.poldi_db4)
        radar = s.query(Radar).filter_by(name="Poldirad").one()
        scan = SRHIData(radar=radar, start_time=handle['start_time'])
        scan2 = SRHIData(radar=radar, start_time=handle['start_time'])
        s.add(scan)
        s.add(scan2)
        s.commit()
        with PoldiDataBase(self.poldi_path, self.poldi_db4,
                           update=False, recheck=False) as poldi_db:
            self.assertRaises(AssertionError, poldi_db.update_db, False)

    def update_and_count(self, path, db, recheck):
        with PoldiDataBase(path, db, recheck=recheck) as poldi_db:
            poldi_db.update_db()
        s = create_session(db)
        q1 = s.query(PPIData).all()
        q2 = s.query(RHIData).all()
        self.assertEqual(len(q1 + q2), 5)


if __name__ == "__main__":
    unittest.main()
