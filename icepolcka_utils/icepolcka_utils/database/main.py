"""Main Database module

This module contains the main database class and utility functions that are used by the
specific database classes implemented in other modules.

"""
import os
import datetime as dt

import sqlalchemy as sql
from sqlalchemy import orm

from icepolcka_utils.database import tables


class DataBase:
    """Main database

    This is the main database class for interaction with a user. This class is abstract, that means
    is has actually no implemented  methods, except for some private methods that are the same for
    the subclasses. All public methods are specifically implemented within the corresponding
    subclasses. The purpose of this method is to document the methods that all subclasses have in
    common and to define private methods that all subclasses have in common.

    When initializing an instance of these classes, a data path to the database and to a sql db file
    must be given. The sql file contains some metadata for each scan and is used to quickly search
    through the database without having to open each file. When the sql file given to the instance
    does not exist, it will be created. Otherwise, it will only be updated with missing files within
    the database. When initializing, the user can decide to put 'update' to False, which means the
    database file will not be updated with new files.

    The initialization should be done in a 'with' statement. This will invoke the __enter__ method
    that checks for potential database updates and afterwards, the database will be closed again.

    Example:

    .. code-block:: python

        with DataBase(data_path, db, update=update) as data_base:
            data_base.do_something()

    :param data_path: Path to the data files.
    :type data_path: str
    :param db_path: Path to the .db database file.
    :type db_path: str
    :param update: Whether to update the database with new files.
    :type update: bool

    """
    def __init__(self, data_path, db_path, update=False):
        self._data_path = data_path
        self._db = "sqlite:///" + db_path
        self._update = update
        self._session = None
        if not os.path.exists(db_path):
            tables.create_tables(db_path)

    def get_closest_data(self, time, **kwargs):
        """Get the closest data to input time

        Given a date time input, this method will return the data set closest to this time.

        :param time: Time [UTC], to which the closest data is returned.
        :type time: ~datetime.datetime

        Here is a list of all keyword arguments. Not all are applicable for each class.

        Keyword Arguments:
            source (str):
                Whether the data comes from 'DWD' or 'MODEL' data.
            mp_id (int):
                WRF ID of a microphysics scheme to be returned.
            method (str):
                Method used for classification. Currently, only 'Dolan' implemented.
            radar (str):
                Name of simulated radar.
            domain (str):
                Name of the model domain.
            hm (str):
                Name of the simulated hydrometeor class.

        Returns:
            ResultHandle :
                The corresponding data closest to input time.

        """
        raise NotImplementedError("Implemented in child class")

    def get_data(self, start_time, end_time, **kwargs):
        """Gets data in given time range

        Given a start and an end time, this method returns the data within this time period.

        :param start_time: Start time of data slice [UTC].
        :type start_time: ~datetime.datetime
        :param end_time: End time of data slice [UTC].
        :type end_time: ~datetime.datetime

        Here is a list of all keyword arguments. Not all are applicable for each class.

        Keyword Arguments:
            source (str):
                Whether the data comes from 'DWD' or 'MODEL' data.
            mp_id (int):
                WRF ID of a microphysics scheme to be returned.
            method (str):
                Method used for classification. Currently, only 'Dolan' implemented.
            radar (str):
                Name of simulated radar.
            domain (str):
                Name of the model domain.
            hm (str):
                Name of the simulated hydrometeor class.

        Returns:
            list:
                List of :class:`~icepolcka_utils.database.handles.ResultHandle` objects, one for
                each data file within the requested time range.

        """
        raise NotImplementedError("Implemented in child class")

    def get_latest_data(self, latest_n=1, **kwargs):
        """Find the latest data set

        This method finds the latest data files within the database.

        :param latest_n: Number of the latest data files to be returned.
        :type latest_n: int

        Here is a list of all keyword arguments. Not all are applicable for each class.

        Keyword Arguments:
            source (str):
                Whether the data comes from 'DWD' or 'MODEL' data.
            mp_id (int):
                WRF ID of a microphysics scheme to be returned.
            method (str):
                Method used for classification. Currently, only 'Dolan' implemented.
            radar (str):
                Name of simulated radar.
            domain (str):
                Name of the model domain.
            hm (str):
                Name of the simulated hydrometeor class.

        Returns:
            list:
                List of :class:`~icepolcka_utils.database.handles.ResultHandle` objects, that
                correspond to the latest data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """
        raise NotImplementedError("Implemented in child class")

    def update_db(self):
        """Update database with new files

        If there are new data files in the data path, this method adds them to the database.

        """
        raise NotImplementedError("Implemented in child class")

    def _add_file_to_db(self, file_path, file_ending, available_filenames):
        if file_path in available_filenames:
            return False
        file_type = self._session.query(tables.FileType).filter(
            tables.FileType.name == file_ending
            ).one()
        data_file = tables.Datafile(filename=file_path, file_type_id=file_type.id)
        self._session.add(data_file)
        return data_file

    def _enter(self):
        engine = sql.create_engine(self._db)
        tables.Base.metadata.bind = engine
        tables.Base.metadata.create_all(engine)
        self._session = orm.sessionmaker(bind=engine)()
        if self._update:
            self.update_db()
        return self

    def _get_available_files(self):
        available_files = self._session.query(tables.Datafile).all()
        available_filenames = [x.filename for x in available_files]
        return available_filenames


def get_closest(query, col, time):
    """Get the closest data in time

    Returns the closest row to input date time. This function is used by multiple database classes
    to find data closest to a given input time.

    :param query: SQL query to be searched for the closest row in time.
    :type query: ~sqlalchemy.orm.query.Query
    :param col: SQL table column.
    :type col: ~sqlalchemy.orm.attributes.InstrumentedAttribute
    :param time: Input time [UTC].
    :type time: ~datetime.datetime

    Returns:
        Child class of :obj:`~sqlalchemy.schema.Table` \
        (e.g. :class:`~icepolcka_utils.database.tables.CRSIMData`):

            The table row that is closest to input time.

    """
    # Split data in two --> Data before and after the input time.
    # This makes sorting easy to find the two entries closest to input time.
    greater = query.filter(col > time).order_by(col.asc()).first()
    lesser = query.filter(col <= time).order_by(col.desc()).first()

    # If one of the splits is None that means only timesteps before or after the
    # input time exist, and we can directly return the one that is not None
    if greater is None:
        return lesser
    if lesser is None:
        return greater

    # If data exists before and after the input time, we find the closest data by calculating the
    # time difference and return the data where this difference is smaller
    greater_dif = abs(getattr(greater, col.name) - time)
    lesser_dif = abs(getattr(lesser, col.name) - time)
    if greater_dif < lesser_dif:
        return greater
    return lesser


def get_handles(db_class, cfg, key, **kwargs):
    """Get handles

    Convenience function to return data handles from the given database with the given
    configuration.

    :param db_class: Database class that is accessed.
    :type db_class: Child of :class:`.DataBase`
    :param cfg: Configuration dictionary.
    :type cfg: dict
    :param key: Defines which data is accessed (e.g., 'WRF'). Used to find the correct data path in
        the configuration dictionary.
    :type key: str
    :param kwargs: Optional arguments. Options depend on the database and are documented in the
        corresponding database class.

    Returns:
        list:
            List of the :class:`~icepolcka_utils.database.handles.ResultHandle` corresponding to \
                the requested data.

    """
    # The DWD data does not have a WRF microphysics ID. The get_data method breaks if both are
    # passed. --> Remove mp_id for DWD data.
    if "source" in kwargs and "mp_id" in kwargs:
        if kwargs['source'] == "DWD":
            del kwargs['mp_id']
    with db_class(cfg['data'][key], cfg['database'][key], update=cfg['update']) as open_db:
        handles = open_db.get_data(cfg['start'], cfg['end'], **kwargs)
    return handles


def update_db(db_class, cfg, key):
    """Update database

    This function just opens the database class to trigger the :meth:`DataBase.update_db` method.

    :param db_class: Database class that is accessed.
    :type db_class: Child of :class:`.DataBase`
    :param cfg: Configuration dictionary.
    :type cfg: dict
    :param key: Defines which data is accessed (e.g., 'WRF'). Used to find the correct data path in
        the configuration dictionary.
    :type key: str

    """
    with db_class(cfg['data'][key], cfg['database'][key], update=True):
        pass
