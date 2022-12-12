"""Model Database module

This module contains all database classes and functions that are related to some kind of model,
such as WRF or CR-SIM.

"""
import os
import datetime as dt
import numpy as np

import sqlalchemy as sql
from sqlalchemy import orm

from icepolcka_utils.database import handles, main, tables


class CRSIMDataBase(main.DataBase):
    """Database of CR-SIM data

    This class serves as an API to access the CR-SIM data. For full documentation on how this class
    is used, see documentation of super class: :class:`~icepolcka_utils.database.main.DataBase` .
    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self._loader = handles.load_xarray

    def __enter__(self):
        engine = sql.create_engine(self._db)
        tables.Base.metadata.bind = engine
        tables.Base.metadata.create_all(engine)
        self._session = orm.sessionmaker(bind=engine)()
        if self._update:
            self.update_db()
        return self

    def __exit__(self, *args):
        self._session.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query(**kwargs)
        closest = main.get_closest(query, tables.CRSIMData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.CRSIMData.time <= end_time).filter(
            tables.CRSIMData.time >= start_time
            )
        query = query.order_by(tables.CRSIMData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.CRSIMData.time.desc()).limit(latest_n)
        return list(map(self._return_data, query.all()))

    def update_db(self):
        available_filenames = self._get_available_files()
        for subdir, _, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".nc"):
                    continue

                data_file = self._add_file_to_db(file_path, "nc", available_filenames)
                if not data_file:
                    continue

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                data = handles.load_xarray(file_path)

                # Query corresponding data base entries
                mp_scheme = self._session.query(tables.MPScheme).filter(
                    tables.MPScheme.id == int(data.MP_PHYSICS)
                    ).one()
                radar = self._session.query(tables.Radar).filter(
                    tables.Radar.name == data.radar
                    ).one()
                hm_entry = self._session.query(tables.Hydrometeor).filter(
                    tables.Hydrometeor.name == data.hydrometeor
                    ).one()

                # Find if data entry exists already
                crsim_data = self._session.query(tables.CRSIMData).filter(
                    tables.CRSIMData.file_path == file_path
                    ).all()

                # If no data entry exist yet, make new entry
                if len(crsim_data) == 0:
                    new_entry = tables.CRSIMData(
                        file_path=file_path, time=dt.datetime.strptime(str(data['time'].values),
                                                                       "%Y-%m-%dT%H:%M:%S.%f000"),
                        mp=mp_scheme, radar=radar, hm=hm_entry
                        )
                    self._session.add(new_entry)
                self._session.commit()
                data.close()
        self._session.commit()

    def _get_query(self, **kwargs):
        query = self._session.query(tables.CRSIMData)
        if "mp_id" in kwargs:
            query = query.filter(tables.CRSIMData.mp_id == int(kwargs['mp_id']))
        if "hm" in kwargs:
            hm_id = self._session.query(tables.Hydrometeor).filter(
                tables.Hydrometeor.name == kwargs['hm']
                ).one().id
            query = query.filter(tables.CRSIMData.hm_id == hm_id)
        if "radar" in kwargs:
            radar_id = self._session.query(tables.Radar).filter(
                tables.Radar.name == kwargs["radar"]
                ).one().id
            query = query.filter(tables.CRSIMData.radar_id == radar_id)
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time, 'mp': query.mp_id,
                 'radar': query.radar.name, 'hm': query.hm.name}
        data_handle = handles.ResultHandle(attrs, lambda: self._loader(attrs['file_path']))
        return data_handle


class WRFDataBase(main.DataBase):
    """Database of WRF data

    This class serves as an API to access the WRF data. For full documentation on how this class
    is used, see documentation of super class: :class:`~icepolcka_utils.database.main.DataBase` .

    Note:
        The WRF files are used for CR-SIM simulations in my work. The CR-SIM data does not save
        any information about the time of the scene, but it saves the name of the mother WRF file.
        That's why I extract time and date from the WRF file name. WRF files are thus always be
        named in the following manner: Y-%m-%d_%H%M%S

        Example: /some/path/wrfout_d03_2019-07-01_120000

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self.model = None
        self.wrf_data = None

    def __enter__(self):
        engine = sql.create_engine(self._db)
        tables.Base.metadata.bind = engine
        tables.Base.metadata.create_all(engine)
        self._session = orm.sessionmaker(bind=engine)()
        self.model = self._session.query(tables.Model).filter(
            tables.Model.name == "WRF"
            ).one()
        if self._update:
            self.update_db()
        return self

    def __exit__(self, *args):
        self._session.close()
        if self.wrf_data is not None:
            self.wrf_data.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query(**kwargs)
        # We assume that start_time equals end_time, which is for my WRF files the case
        closest = main.get_closest(query, tables.Dataset.start_time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.Dataset.start_time >= start_time).filter(
            tables.Dataset.end_time <= end_time
            )
        query = query.order_by(tables.Dataset.start_time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.Dataset.start_time.desc()).limit(latest_n)
        return list(map(self._return_data, query.all()))

    def update_db(self):
        available_filenames = self._get_available_files()
        for subdir, _, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)
                file_type_name = self._get_file_type_name(file)
                if not file_type_name:
                    print("Not a valid data file: ", file_path)
                    continue

                # Date and time are found from the file name.
                try:
                    dt.datetime.strptime(str(file.split("_")[2]) + "_" + str(file.split("_")[3]),
                                         "%Y-%m-%d_%H%M%S")
                except ValueError:
                    print("File " + file_path + " does not match the file name requested file name"
                                                " format: %Y-%m-%d_%H%M%S. Skipping this file")
                    continue

                data_file = self._add_file_to_db(file_path, file_type_name, available_filenames)
                if not data_file:
                    continue

                # Up to now, only the data file entry was added to the database. Below, the
                # datafile is opened and all information of interest will be saved to the database
                # tables.
                print("Updating: ", file_path)
                self.wrf_data = handles.load_wrf_data(file_path)
                domain = self._session.query(tables.Domain).filter(
                    tables.Domain.x_res == self.wrf_data.DX
                    ).filter(tables.Domain.y_res == self.wrf_data.DY).filter(
                    tables.Domain.lon_0 == np.round(float(self.wrf_data.CEN_LON), decimals=6)
                    ).filter(
                    tables.Domain.lat_0 == np.round(float(self.wrf_data.CEN_LAT), decimals=6)
                    ).one()
                mp_scheme = self._session.query(tables.MPScheme).filter(
                    tables.MPScheme.id == int(self.wrf_data.MP_PHYSICS)
                    ).one()

                dataset, model_data = self._get_dataset(mp_scheme, domain)

                # The currently updated file can have different types. Add it to the correct column
                # depending on the file_type
                if file_type_name == "clouds":
                    dataset.clouds_file = data_file
                elif file_type_name == "wrfmp":
                    dataset.wrfmp_file = data_file
                elif file_type_name == "wrfout":
                    dataset.wrfout_file = data_file

                model_data.model = self.model
                model_data.dataset = dataset
                self._session.add(dataset)
                self._session.add(model_data)
                self._session.commit()
        self._session.commit()

    def _get_dataset(self, mp_scheme, domain):
        start_time = dt.datetime.strptime(str(self.wrf_data.Time.values[0]),
                                          "%Y-%m-%dT%H:%M:%S.%f000")
        end_time = dt.datetime.strptime(str(self.wrf_data.Time.values[-1]),
                                        "%Y-%m-%dT%H:%M:%S.%f000")
        # Multiple files can correspond to the same dataset (E.g., wrfout, wrfmp and clouds files of
        # the same timestep). These files are assigned to the same dataset. Find out first, if a
        # dataset exists already for the current file.
        existing_dataset = self._session.query(tables.Dataset).filter(
            tables.Dataset.start_time == start_time
            ).filter(tables.Dataset.end_time == end_time).filter(
            tables.Dataset.mp == mp_scheme
            ).filter(tables.Dataset.domain == domain).filter(
            tables.Dataset.model_id == self.model.id
            ).all()

        # If existing_dataset is empty, that means a dataset corresponding to the current file
        # doesn't exist yet. Create a new Dataset and a new ModelData entry. If it is not empty, the
        # corresponding dataset is in the list and a ModelData entry should exist already that was
        # assigned to this Dataset.
        if len(existing_dataset) == 0:
            dataset = tables.Dataset(start_time=start_time, end_time=end_time,
                                     domain=domain, mp=mp_scheme, model=self.model)
            model_data = tables.ModelData()
            return dataset, model_data
        if len(existing_dataset) == 1:
            dataset = existing_dataset[0]
            model_data = self._session.query(tables.ModelData).filter(
                tables.ModelData.dataset == dataset
                ).one()
            return dataset, model_data
        raise AssertionError("Length of dataset must be 0 or 1")

    @staticmethod
    def _get_file_type_name(file):
        # The WRF filetype is defined with the name. The name always starts with the type of
        # data (wrfmp, clouds or wrfout).
        if file.startswith("clouds"):
            file_type_name = "clouds"
        elif file.startswith("wrfmp"):
            file_type_name = "wrfmp"
        elif file.startswith("wrfout"):
            file_type_name = "wrfout"
        else:
            return False
        return file_type_name

    def _get_query(self, **kwargs):
        query = self._session.query(tables.Dataset).filter(
            tables.ModelData.model_id == self.model.id
            )
        if "domain" in kwargs:
            domain_id = self._session.query(tables.Domain).filter(
                tables.Domain.name == kwargs['domain']
                ).one().id
            query = query.filter(tables.Dataset.domain_id == domain_id)
        if "mp_id" in kwargs:
            query = query.filter(tables.Dataset.mp_id == int(kwargs['mp_id']))
        return query

    @staticmethod
    def _return_data(query):
        assert query is not None, "No data found corresponding to request"
        handle = {}
        if query.wrfout_file:
            wrfout_attrs = {'file_path': query.wrfout_file.filename,
                            'start_time': query.start_time, 'end_time': query.end_time,
                            'domain': query.domain, 'mp_id': query.mp_id}
            wrfout_handle = handles.ResultHandle(wrfout_attrs, lambda: handles.load_wrf_data(
                query.wrfout_file.filename)
                                                 )
            handle['wrfout'] = wrfout_handle
        if query.clouds_file:
            clouds_attrs = {'file_path': query.clouds_file.filename,
                            'start_time': query.start_time, 'end_time': query.end_time,
                            'domain': query.domain, 'mp_id': query.mp_id}
            clouds_handle = handles.ResultHandle(clouds_attrs, lambda: handles.load_wrf_data(
                query.clouds_file.filename)
                                                 )
            handle['clouds'] = clouds_handle
        if query.wrfmp_file:
            wrfmp_attrs = {'file_path': query.wrfmp_file.filename,
                           'start_time': query.start_time, 'end_time': query.end_time,
                           'domain': query.domain, 'mp_id': query.mp_id}
            wrfmp_handle = handles.ResultHandle(wrfmp_attrs, lambda: handles.load_wrf_data(
                query.wrfmp_file.filename)
                                                )
            handle['wrfmp'] = wrfmp_handle
        return handle


def get_wrf_handles(cfg, wrfout=False, wrfmp=False):
    """Get wrf handles

    WRF database must be opened date by date, because it is too big to open everything at once.
    The corresponding data handles are found for each date and appended to a final list which is
    returned in the end

    :param cfg: Configuration dictionary.
    :type cfg: dict
    :param wrfmp: if True, wrfmp handles will be returned too. The wrfmp files are files specific
        to the spectral bin simulations where the particle size distributions are saved within the
        wrfmp files.
    :type wrfmp: bool
    :param wrfout: if True, wrfout handles will be returned too. The wrfout files are hourly output
        files with the complete WRF output.
    :type wrfout: bool

    Returns:
        tuple:
            Tuple (all_clouds, all_wrfmp, all_wrfout), with:

                - all_clouds (:obj:`list`): List of all clouds data handles corresponding \
                    configuration.
                - all_wrfmp (:obj:`list`): List of all wrfmp data handles corresponding to \
                    configuration. Empty, if wrfmp argument is False.
                - all_wrfout (:obj:`list`): List of all wrfout data handles corresponding to \
                    configuration. Empty, if wrfout argument is False.


    """
    all_clouds, all_wrfout, all_wrfmp = [], [], []
    step_start = cfg['start']
    step_end = cfg['start'] + dt.timedelta(days=1)  # First day
    stop = False

    with WRFDataBase(cfg['data']['WRF'], cfg['database']['WRF'], update=cfg['update']) as wrf_db:
        # The loop breaks when the configured end time is reached
        while True:

            # If end variable > configured end, reset it to the configured end and do the loop one
            # last time to find data from last day
            if step_end > cfg['end']:
                step_end = cfg['end']
                stop = True

            # Find data corresponding to configuration
            wrf_handles = wrf_db.get_data(step_start, step_end, mp_id=cfg['mp'], domain="Munich")

            # Load only cloud files and append to final list
            clouds_handles = [h['clouds'] for h in wrf_handles if "clouds" in h.keys()]
            all_clouds += clouds_handles
            if wrfmp:
                wrfmp_handles = [h['wrfmp'] for h in wrf_handles if "wrfmp" in h.keys()]
                all_wrfmp += wrfmp_handles
            if wrfout:
                wrfout_handles = [h['wrfout'] for h in wrf_handles if "wrfout" in h.keys()]
                all_wrfout += wrfout_handles

            # Increase start and end variable by one day
            step_start = step_start + dt.timedelta(days=1)
            step_end = step_end + dt.timedelta(days=1)

            # Break loop if last date was processed
            if stop:
                break

    return all_clouds, all_wrfout, all_wrfmp
