"""Interpolations Database module

This module contains all database classes and functions that are related to data after my
interpolations, such as the regular grid database.

"""
import os
import datetime as dt

from icepolcka_utils.database import handles, main, tables


class RFDataBase(main.DataBase):
    """Database of radar filter data

    The CR-SIM data is transformed from a Cartesian to a spherical grid with the radar filter. This
    class serves as an API to access this radar filter data. For full documentation on how this
    class is used, see documentation of super class:
    :class:`~icepolcka_utils.database.main.DataBase` .

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self._loader = handles.load_xarray

    def __enter__(self):
        return self._enter()

    def __exit__(self, *args):
        self._session.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query(**kwargs)
        closest = main.get_closest(query, tables.RFData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.RFData.time >= start_time).filter(
            tables.RFData.time <= end_time
            )
        query = query.order_by(tables.RFData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.RFData.time.desc()).limit(latest_n)
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
                rf_time = dt.datetime.strptime(str(data.time.values), "%Y-%m-%dT%H:%M:%S.%f000")

                # Query corresponding data base entries
                mp_scheme = self._session.query(tables.MPScheme).filter(
                    tables.MPScheme.id == int(data.MP_PHYSICS)
                    ).one()
                radar = self._session.query(tables.Radar).filter(
                    tables.Radar.name == data.radar
                    ).one()

                # Find if data entry exists already
                rf_data = self._session.query(tables.RFData).filter(
                    tables.RFData.file_path == file_path
                    ).all()

                # If no entry exist yet - make new entry
                if len(rf_data) == 0:
                    new_entry = tables.RFData(file_path=file_path, time=rf_time, mp=mp_scheme,
                                              radar=radar)
                    self._session.add(new_entry)

                self._session.commit()
                data.close()
        self._session.commit()

    def _get_query(self, **kwargs):
        query = self._session.query(tables.RFData)
        if "mp_id" in kwargs:
            query = query.filter(tables.RFData.mp_id == int(kwargs['mp_id']))
        if "radar" in kwargs:
            radar_id = self._session.query(tables.Radar).filter(
                tables.Radar.name == kwargs['radar']
                ).one().id
            query = query.filter(tables.RFData.radar_id == radar_id)
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time, 'mp': query.mp_id,
                 'radar': query.radar.name}
        data_handle = handles.ResultHandle(
            attrs, lambda: self._loader(attrs['file_path'])
            )
        return data_handle


class RGDataBase(main.DataBase):
    """Database of regular grid data

    Interpolating CR-SIM or DWD data to a regular Cartesian grid is a common task. To not have to
    repeat it at ech plotting script, the interpolation to the regular grid is done once and saved.
    This class serves as an API to access this data. For full documentation on how this class is
    used, see documentation of super class: :class:`~icepolcka_utils.database.main.DataBase` .

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self._loader = handles.load_xarray

    def __enter__(self):
        return self._enter()

    def __exit__(self, *args):
        self._session.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query(**kwargs)
        closest = main.get_closest(query, tables.RGData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.RGData.time <= end_time).filter(
            tables.RGData.time >= start_time
            )
        query = query.order_by(tables.RGData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.RGData.time.desc()).limit(latest_n)
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

                # Load data
                data = handles.load_xarray(file_path)
                time = dt.datetime.strptime(str(data.attrs['time']), "%Y-%m-%d %H:%M:%S")

                # Query corresponding data base entries
                try:
                    mp_scheme = self._session.query(tables.MPScheme).filter(
                        tables.MPScheme.id == int(data.MP_PHYSICS)
                        ).one()
                except AttributeError:
                    mp_scheme = None
                radar = self._session.query(tables.Radar).filter(
                    tables.Radar.name == data.radar
                    ).one()

                # Find if data entry exists already
                existing_data = self._session.query(tables.RGData).filter(
                    tables.RGData.file_path == file_path
                    ).all()

                # If no entry exist yet - make new entry
                if len(existing_data) == 0:
                    new_entry = tables.RGData(file_path=file_path, time=time, source=data.source,
                                              mp=mp_scheme, radar=radar)
                    self._session.add(new_entry)

                self._session.commit()
                data.close()
        self._session.commit()

    def _get_query(self, **kwargs):
        query = self._session.query(tables.RGData)
        if "source" in kwargs:
            query = query.filter(tables.RGData.source == kwargs['source'])
        if "mp_id" in kwargs:
            query = query.filter(tables.RGData.mp_id == int(kwargs['mp_id']))
        if "radar" in kwargs:
            radar_id = self._session.query(tables.Radar).filter(
                tables.Radar.name == kwargs['radar']
                ).one().id
            query = query.filter(tables.RGData.radar_id == radar_id)
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time, 'source': query.source,
                 'mp': query.mp_id, 'radar': query.radar.name}
        data_handle = handles.ResultHandle(attrs, lambda: self._loader(attrs['file_path']))
        return data_handle


class TempDataBase(main.DataBase):
    """Database of temperature grid

    Temperature was interpolated to the regular grid. This class serves as an API to access these
    temperature grids. For full documentation on how this class is used, see documentation of super
    class: :class:`~icepolcka_utils.database.main.DataBase` .

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self._loader = handles.load_xarray

    def __enter__(self):
        return self._enter()

    def __exit__(self, *args):
        self._session.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query(**kwargs)
        closest = main.get_closest(query, tables.TempData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.TempData.time <= end_time).filter(
            tables.TempData.time >= start_time
            )
        query = query.order_by(tables.TempData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.TempData.time.desc()).limit(latest_n)
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

                # Load data
                data = handles.load_xarray(file_path)
                time = dt.datetime.strptime(str(data['time'].values), "%Y-%m-%dT%H:%M:%S.%f000")

                # Query corresponding data base entries
                mp_scheme = self._session.query(tables.MPScheme).filter(
                    tables.MPScheme.id == int(data.MP_PHYSICS)
                    ).one()

                # Find if data entry exists already
                existing_data = self._session.query(tables.TempData).filter(
                    tables.TempData.file_path == file_path
                    ).all()

                # If no entry exist yet - make new entry
                if len(existing_data) == 0:
                    new_entry = tables.TempData(file_path=file_path, time=time, mp=mp_scheme)
                    self._session.add(new_entry)

                self._session.commit()
                data.close()
        self._session.commit()

    def _get_query(self, **kwargs):
        query = self._session.query(tables.TempData)
        if "mp_id" in kwargs:
            query = query.filter(tables.TempData.mp_id == int(kwargs['mp_id']))
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time,
                 'mp': query.mp_id}
        data_handle = handles.ResultHandle(attrs, lambda: self._loader(attrs['file_path']))
        return data_handle
