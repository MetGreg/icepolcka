"""Radars Database module

This module contains all database classes and functions that are related to radar data.

"""

import os
import datetime as dt

import sqlalchemy as sql
from sqlalchemy import orm

from icepolcka_utils.database import handles, main, tables


class RadarDataBase(main.DataBase):
    """Abstract radar database

    This is the main radar data class for interaction with a user. This class is abstract, that
    means is has actually no implemented methods, except one private method that is used by
    multiple subclasses. All methods are specifically implemented within the corresponding
    subclass :class:`DWDDataBase`.

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self.radar = None

    def get_closest_data(self, time, **kwargs):
        raise NotImplementedError("Does not apply for this class")

    def get_data(self, start_time, end_time, **kwargs):
        raise NotImplementedError("Does not apply for this class")

    def get_latest_data(self, latest_n=1, **kwargs):
        raise NotImplementedError("Does not apply for this class")

    def update_db(self):
        raise NotImplementedError("Does not apply for this class")

    def _enter_radar_db(self, radar_name):
        engine = sql.create_engine(self._db)
        tables.Base.metadata.bind = engine
        tables.Base.metadata.create_all(engine)
        self._session = orm.sessionmaker(bind=engine)()
        self.radar = self._session.query(tables.Radar).filter(
            tables.Radar.name == radar_name
            ).one()
        if self._update:
            self.update_db()
        return self


class DWDDataBase(RadarDataBase):
    """Radar database of DWD volume data.

    This class serves as an API to access DWD data. For full documentation on how this
    class is used, see documentation of super class:
    :class:`~icepolcka_utils.database.main.DataBase` .
 

    """
    def __init__(self, data_path, db_path, update=False):
        super().__init__(data_path, db_path, update)
        self._handler = handles.DWDDataHandler()

    def __enter__(self):
        return self._enter_radar_db("Isen")

    def __exit__(self, *args):
        self._session.close()

    def get_closest_data(self, time, **kwargs):
        query = self._get_query()
        closest = main.get_closest(query, tables.DWDData.time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time, **kwargs):
        query = self._get_query()
        query = query.filter(
            tables.DWDData.time >= start_time
            ).filter(
            tables.DWDData.time <= end_time
            )
        query = query.order_by(tables.DWDData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_latest_data(self, latest_n=1, **kwargs):
        query = self._get_query()
        query = query.order_by(tables.DWDData.time.desc()).limit(latest_n)
        return list(map(self._return_data, query.all()))

    def update_db(self):
        available_files = self._session.query(tables.Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, _, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".hd5"):
                    continue
                if file_path.endswith("20190528.hd5"):  # Wrong file in archive
                    continue

                data_file = self._add_file_to_db(file_path, "hdf5", available_filenames)
                if not data_file:  # Data file was added already to db - skip it
                    continue

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                scan_data = self._handler.load_data(file_path)
                time = dt.datetime.strptime(str(scan_data['time']), "%Y-%m-%d %H:%M:%S")

                # Find if data entry exists already
                dwd_data = self._session.query(tables.DWDData).filter(
                    tables.DWDData.file_path == file_path
                    ).all()

                # If no data entry exist yet, make new entry
                if len(dwd_data) == 0:
                    new_entry = tables.DWDData(file_path=file_path, time=time)
                    self._session.add(new_entry)
                self._session.commit()

                # Close data files
                for _, scan_ds in scan_data.items():
                    try:
                        scan_ds.close()
                    except AttributeError:
                        continue
        self._session.commit()

    def _get_query(self):
        query = self._session.query(tables.DWDData)
        return query

    def _return_data(self, query):
        assert query is not None, "No data found corresponding to request"
        attrs = {'file_path': query.file_path, 'time': query.time}
        data_handle = handles.ResultHandle(attrs,
                                           lambda: self._handler.load_data(attrs['file_path']))
        return data_handle
