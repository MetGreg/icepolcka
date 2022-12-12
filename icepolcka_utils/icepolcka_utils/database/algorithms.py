"""Algorithms Database module

This module contains all database classes and functions that are related to some kind of algorithm,
such as the hydrometeor classification algorithm.

"""
import os
import datetime as dt

from icepolcka_utils.database import handles, main, tables


class HMCDataBase(main.DataBase):
    """Database of hydrometeor classification data

    Within the IcePolCKa project, a hydrometeor classification (hmc) algorithm was applied on the
    (simulated) radar signal fields. The HMC algorithm output was saved to netcdf files. This
    class serves as an API to access this data. For full documentation on how this class is used,
    see documentation of super class: :class:`~icepolcka_utils.database.main.DataBase` .

    See Also:
        Dolan, B. et al.: "A robust C-band hydrometeor identification algorithm and
        application to a long-term polarimetric radar dataset." Journal of Applied Meteorology and
        Climatology 52.9, 2162-2186, https://doi.org/10.1175/JAMC-D-12-0275.1, 2013.

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
        closest = main.get_closest(query, tables.HMCData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query(**kwargs)
        query = query.filter(tables.HMCData.time <= end_time).filter(
            tables.HMCData.time >= start_time
            )
        query = query.order_by(tables.HMCData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query(**kwargs)
        query = query.order_by(tables.HMCData.time.desc()).limit(latest_n)
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
                data = self._loader(file_path)
                time = dt.datetime.strptime(str(data.time), "%Y-%m-%d %H:%M:%S")

                # Query corresponding data base entries
                mp_scheme = self._session.query(tables.MPScheme).filter(
                    tables.MPScheme.id == int(data.MP_PHYSICS)
                    ).one()

                # Find if data entry exists already
                existing_data = self._session.query(tables.HMCData).filter(
                    tables.HMCData.file_path == file_path
                    ).all()

                # If no data entry exist yet, make new entry
                if len(existing_data) == 0:
                    new_entry = tables.HMCData(file_path=file_path, time=time, source=data.source,
                                               mp=mp_scheme, method=data.method)
                    self._session.add(new_entry)

                self._session.commit()
                data.close()
        self._session.commit()

    def _get_query(self, **kwargs):
        query = self._session.query(tables.HMCData)
        if "source" in kwargs:
            query = query.filter(tables.HMCData.source == kwargs['source'])
        if "mp_id" in kwargs:
            query = query.filter(tables.HMCData.mp_id == int(kwargs['mp_id']))
        if "method" in kwargs:
            query = query.filter(tables.HMCData.method == kwargs['method'])
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time, 'source': query.source,
                 'mp': query.mp_id, 'method': query.method}
        data_handle = handles.ResultHandle(attrs, lambda: self._loader(attrs['file_path']))
        return data_handle
