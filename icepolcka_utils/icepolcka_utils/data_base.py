"""Data base module

This module contains all data base classes.

All of the classes are SQL based data bases. The SQL tables are defined using
an ORM-approach with SQLAlchemy. These classes are simply tables that define
the columns of the SQL table.

The actual Data Base classes are useful to access data that is saved in
some data folder. They will update a .db file with meta data about all files
within the data folder. The data bases can then be used to access the data with
an API, where the SQL based approach helps to find data quickly.

"""
import os
import datetime as dt
import numpy as np
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, \
    create_engine
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from icepolcka_utils.handles import WRFDataHandler, CRSIMDataHandler, \
    DWDDataHandler, RFDataHandler, RGDataHandler, TracksDataHandler, \
    MiraDataHandler, PoldiDataHandler, ResultHandle

Base = declarative_base()


def create_session(db):
    """Create SQL session

    Args:
        db (str): Path to data

    Returns:
        sqlalchemy.orm.session.Session:
            The current session.

    """
    engine = create_engine("sqlite:///" + db)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    return s


def create_db(db, s=None):
    """Create the basic data base structure

    This should only be called when the data base doesn't exist yet.

    Args:
        db (str): Name of data base.
        s (sqlalchemy.orm.session.Session): Potential existing session.

    Returns:
        sqlalchemy.orm.session.Session:
            The current session.

    """
    if s is None:
        s = create_session(db)

    # Create file types
    nc = FileType(name="nc")
    mmclx = FileType(name="mmclx")
    clouds = FileType(name="clouds")
    wrfmp = FileType(name="wrfmp")
    wrfout = FileType(name="wrfout")
    hdf5 = FileType(name="hdf5")
    corrupt = FileType(name="corrupt")

    # Create models
    wrf = Model(name="WRF")

    # Create domains
    europe = Domain(name="Europe", x_res=10000, y_res=10000, lon_0=7.5,
                    lat_0=50.000015, x_dim=374, y_dim=374, z_dim=39)
    germany = Domain(name="Germany", x_res=2000, y_res=2000, lon_0=11.547821,
                     lat_0=48.165325, x_dim=220, y_dim=220, z_dim=39)
    munich = Domain(name="Munich", x_res=400, y_res=400, lon_0=11.574249,
                    lat_0=48.145794, x_dim=360, y_dim=360, z_dim=39)

    # Create mp-schemes
    kessler = MPScheme(id=1, name="Kessler")
    thompson = MPScheme(id=8, name="Thompson")
    morrison = MPScheme(id=10, name="Morrison")
    thompson_aerosol = MPScheme(id=28, name="Thompson Aerosol Aware")
    sbm = MPScheme(id=30, name="Fast Spectral Bin")
    p3 = MPScheme(id=50, name="P3")

    # Create radars
    isen = Radar(name="Isen", frequency=5.5, height=678, beamwidth=1.0,
                 sensitivity=-50, longitude=12.101779, latitude=48.174705)
    poldi = Radar(name="Poldirad", frequency=5.5, height=603,
                  beamwidth=1.0, sensitivity=-50, longitude=11.278898,
                  latitude=48.086759)
    mira = Radar(name="Mira35", frequency=35.0, height=541,
                 beamwidth=0.6, sensitivity=-50, longitude=11.573396,
                 latitude=48.147845)

    # Create Hydrometeors
    cloud = Hydrometeor(name="cloud")
    ice = Hydrometeor(name="ice")
    rain = Hydrometeor(name="rain")
    snow = Hydrometeor(name="snow")
    graupel = Hydrometeor(name="graupel")
    parimedice = Hydrometeor(name="parimedice")
    smallice = Hydrometeor(name="smallice")
    unrimedice = Hydrometeor(name="unrimedice")
    all_hm = Hydrometeor(name="all")

    # Add all to session
    s.add_all([nc, mmclx, clouds, wrfmp, wrfout, hdf5, wrf, corrupt, europe,
               germany, munich, kessler, thompson, morrison, thompson_aerosol,
               sbm, p3, isen, poldi, mira, cloud, ice, rain, snow, graupel,
               parimedice, smallice, unrimedice, all_hm])

    # Commit changes
    s.commit()
    return s


def get_closest(query, col, time):
    """Get closest data in time

    Returns the closest row to input date time.

    Args:
        query (sqlalchemy.orm.query.Query): Query to be searched.
        col (sqlalchemy.orm.attributes.InstrumentedAttribute): SQL table
            column.
        time (datetime.datetime): Input time [UTC].

    Returns:
        sqlalchemy data entry:
            The closest table entry.

    """
    greater = query.filter(col > time).order_by(col.asc()).first()
    lesser = query.filter(col <= time).order_by(col.desc()).first()
    if greater is None:
        return lesser
    if lesser is None:
        return greater
    greater_dif = abs(getattr(greater, col.name) - time)
    lesser_dif = abs(getattr(lesser, col.name) - time)

    if greater_dif < lesser_dif:
        return greater
    else:
        return lesser


class FileType(Base):
    __tablename__ = "file_type"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Datafile(Base):
    __tablename__ = "datafile"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    last_checked = Column(DateTime)
    file_type_id = Column(Integer, ForeignKey("file_type.id"))
    file_type = relationship(FileType, backref=backref("datafile",
                                                       uselist=True))


class Model(Base):
    __tablename__ = "model"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Domain(Base):
    __tablename__ = "domain"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    x_res = Column(Float)
    y_res = Column(Float)
    lon_0 = Column(Float)
    lat_0 = Column(Float)
    x_dim = Column(Integer)
    y_dim = Column(Integer)
    z_dim = Column(Integer)


class MPScheme(Base):
    __tablename__ = "mp_scheme"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Dataset(Base):
    __tablename__ = "dataset"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    mmclx_file_id = Column(Integer, ForeignKey("datafile.id"))
    mmclx_file = relationship(Datafile, foreign_keys=[mmclx_file_id],
                              backref=backref("mmclx_dataset", uselist=True))
    nc_file_id = Column(Integer, ForeignKey("datafile.id"))
    nc_file = relationship(Datafile, foreign_keys=[nc_file_id],
                           backref=backref("nc_dataset", uselist=True))
    clouds_file_id = Column(Integer, ForeignKey("datafile.id"))
    clouds_file = relationship(Datafile, foreign_keys=[clouds_file_id],
                               backref=backref("clouds_dataset", uselist=True))
    wrfmp_file_id = Column(Integer, ForeignKey("datafile.id"))
    wrfmp_file = relationship(Datafile, foreign_keys=[wrfmp_file_id],
                              backref=backref("wrfmp_dataset", uselist=True))
    wrfout_file_id = Column(Integer, ForeignKey("datafile.id"))
    wrfout_file = relationship(Datafile, foreign_keys=[wrfout_file_id],
                               backref=backref("wrfout_dataset", uselist=True))
    hdf5_file_id = Column(Integer, ForeignKey("datafile.id"))
    hdf5_file = relationship(Datafile, foreign_keys=[hdf5_file_id],
                             backref=backref("hdf5_dataset", uselist=True))
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    mp = relationship(MPScheme, backref=backref("mp_dataset", uselist=True))
    domain_id = Column(Integer, ForeignKey("domain.id"))
    domain = relationship(Domain,
                          backref=backref("domain_dataset", uselist=True))
    model_id = Column(Integer, ForeignKey("model.id"))
    model = relationship(Model, backref=backref("model_dataset", uselist=True))


class Hydrometeor(Base):
    __tablename__ = "hydrometeor"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Radar(Base):
    __tablename__ = "radar"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    frequency = Column(Float)
    height = Column(Float)
    beamwidth = Column(Float)
    resolution = Column(Float)
    range = Column(Float)
    sensitivity = Column(Float)
    wrf_index_x = Column(Integer)
    wrf_index_y = Column(Integer)
    longitude = Column(Float)
    latitude = Column(Float)


class ModelData(Base):
    __tablename__ = "model_data"
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("model.id"))
    model = relationship(Model, backref=backref("model_data", uselist=True))
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    dataset = relationship(Dataset, backref=backref("model_data", uselist=True))


class CRSIMData(Base):
    __tablename__ = "crsim_data"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    time = Column(DateTime)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("crsim_data", uselist=True))
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    mp = relationship(MPScheme, backref=backref("crsim_data", uselist=True))
    hm_id = Column(Integer, ForeignKey("hydrometeor.id"))
    hm = relationship(Hydrometeor, backref=backref("crsim_data", uselist=True))


class RFData(Base):
    __tablename__ = "radar_filter_data"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    time = Column(DateTime)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("rf_data", uselist=True))
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    mp = relationship(MPScheme, backref=backref("rf_data", uselist=True))


class RGData(Base):
    __tablename__ = "regular_grid_data"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    time = Column(DateTime)
    source = Column(String)
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    mp = relationship(MPScheme, backref=backref("regular_grid_data",
                                                uselist=True))
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("regular_grid_data",
                                                uselist=True))


class TracksData(Base):
    __tablename__ = "tracks_data"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    date = Column(DateTime)
    source = Column(String)
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    mp = relationship(MPScheme, backref=backref("tracks_data", uselist=True))
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("tracks_data", uselist=True))


class DWDData(Base):
    __tablename__ = "dwd_data"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    time = Column(DateTime)


class PPIData(Base):
    __tablename__ = "ppi_data"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    elevation = Column(Float)
    resolution = Column(Float)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("ppi_data", uselist=True))
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    dataset = relationship(Dataset, backref=backref("ppi_data", uselist=True))
    scan_number = Column(Integer)


class SRHIData(Base):
    __tablename__ = "sector_rhi_data"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("sector_rhi_data",
                                                uselist=True))


class RHIData(Base):
    __tablename__ = "rhi_data"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    azimuth = Column(Float)
    resolution = Column(Float)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("rhi_data", uselist=True))
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    dataset = relationship(Dataset, backref=backref("rhi_data", uselist=True))
    sector_rhi_id = Column(Integer, ForeignKey("sector_rhi_data.id"))
    sector_rhi = relationship(SRHIData, backref=backref("rhi_data",
                                                        uselist=True))
    scan_number = Column(Integer)


class HVData(Base):
    __tablename__ = "hv_data"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    radar_id = Column(Integer, ForeignKey("radar.id"))
    radar = relationship(Radar, backref=backref("hv_data", uselist=True))
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    dataset = relationship(Dataset, backref=backref("h_data", uselist=True))


class DataBase(object):
    """Abstract data base

    This is the main data base class for interaction with a user. This class
    is abstract, that means is has actually no implemented methods. All methods
    are specifically implemented within the corresponding subclasses. The
    purpose of this method is to document the methods that all subclasses
    have in common.

    When initializing an instance of these classes, a data path to the data
    base and to a sql db file must be given. The sql file contains
    some meta data for each scan and is used to quickly search through the
    data base without having to open each file. When the sql file given to the
    instance does not exist, it will be created. Otherwise, it will only be
    updated with missing files within the data base. When initializing,
    the user can decide to put 'update' to False, which means the
    data base file will not be updated with new files. When putting 'recheck'
    to False, the files within the data base are not rechecked to see if
    there have been any changes to the files.

    The initialization should be done in a 'with' statement. This will invoke
    the __enter__ method that checks for potential data base updates and
    afterwards, the data base will be closed again.

    Example:

    with DataBase(data_path, db, update=update, recheck=recheck) as data_base:
        data_base.do_something()


    All subclasses have methods that serve as an API to access the data base.
    These API methods are varying between the subclasses, depending on the
    data format, or the attributes that can be used. However, all of them
    have the following methods:

        - :meth:`update_db`:
            Updates the data base with new data.
        - :meth:`get_data`:
            Gets a data slice according to user input.
        - :meth:`get_closest_data`:
            Gets the data closest to input time.
        - :meth:`get_latest_data`:
            Gets the latest 'n' data files.

    The implemented methods within the subclasses have optional arguments,
    that depend on the subclass. This abstract superclass documents only the
    arguments that all have in common. For documentation of the specific
    optional arguments, see the documentation of the specific methods.

    Args:
        data_path (str): Path to data base.
        db (str): Name of data base file.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.

    """
    def get_data(self, start_time, end_time):
        """Gets data in given time range

        This function always needs start- and end-time and returns all data
        for this time range.

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].

        """
        raise NotImplementedError

    def get_closest_data(self, time):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Start time of data slice [UTC].

        """
        raise NotImplementedError

    def get_latest_data(self, n=1):
        """Find latest data

        Returns the latest 'n' data files.
        
        Args:
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of :meth:`ResultHandle` objects that correspond to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.
        """
        raise NotImplementedError

    def update_db(self, recheck=True):
        """Updates the data base with missing data

        Args:
            recheck (Bool): Whether to check data base for changed files.

        """
        raise NotImplementedError


class WRFDataBase(DataBase):
    """Data base of WRF data

    This class serves as an API to access the WRF data. For documentation of
    initialization and general DataBase methods, see super class.

    Note:
        The WRF files are used for CR-SIM simulations in my work. The CR-SIM
        data does not save any information about the time of the scene, but it
        saves the name of the mother WRF file. That's why I extract time and
        date from the WRF file name. WRF files must thus always be named in the
        following manner: Y-%m-%d_%H%M%S

        Example:
            /some/path/wrfout_d03_2019-07-01_120000


    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._db = "sqlite:///" + db
        self._handler = WRFDataHandler()
        self._recheck = recheck
        self._update = update
        if not (os.path.exists(db)):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        self.model = self._session.query(Model).filter(
            Model.name == "WRF"
            ).one()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, ds):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result. This method
        is intended to be internal and should not be called by the user
        directly.

        Args:
            ds (Dataset): Query result.

        Returns:
            dict:
                Dictionary containing the ResultHandles for wrfmp, wrfout and
                    clouds part of the dataset.

        """
        handle = {}
        if ds.wrfout_file:
            wrfout_attrs = {'file_path': ds.wrfout_file.filename,
                            'start_time': ds.start_time,
                            'end_time': ds.end_time, 'domain': ds.domain,
                            'mp_id': ds.mp_id}
            wrfout_handle = ResultHandle(
                wrfout_attrs,
                lambda: self._handler.load_data(ds.wrfout_file.filename)
                )
            handle['wrfout'] = wrfout_handle
        if ds.clouds_file:
            clouds_attrs = {'file_path': ds.clouds_file.filename,
                            'start_time': ds.start_time,
                            'end_time': ds.end_time, 'domain': ds.domain,
                            'mp_id': ds.mp_id}
            clouds_handle = ResultHandle(
                clouds_attrs,
                lambda: self._handler.load_data(ds.clouds_file.filename)
                )
            handle['clouds'] = clouds_handle
        if ds.wrfmp_file:
            wrfmp_attrs = {'file_path': ds.wrfmp_file.filename,
                           'start_time': ds.start_time,
                           'end_time': ds.end_time, 'domain': ds.domain,
                           'mp_id': ds.mp_id}
            wrfmp_handle = ResultHandle(
                wrfmp_attrs,
                lambda: self._handler.load_data(ds.wrfmp_file.filename)
                )
            handle['wrfmp'] = wrfmp_handle
        return handle

    def _get_query(self, domain=None, mp_id=None):
        """Returns the basic query with given input parameters

        Args:
            domain (str): Name of the domain.
            mp_id (int): WRF ID of a microphysics scheme to be returned.

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(Dataset).filter(
            ModelData.model_id == self.model.id
            )
        if domain:
            domain_id = self._session.query(Domain).filter(
                Domain.name == domain
                ).one().id
            query = query.filter(Dataset.domain_id == domain_id)
        if mp_id:
            query = query.filter(Dataset.mp_id == int(mp_id))
        return query

    def get_data(self, start_time, end_time, domain=None, mp_id=None):
        """Gets data in given time range

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].
            domain (str): Name of the domain.
            mp_id (int): ID of a microphysics scheme to be returned.

        Returns:
            list:
                List of dictionaries containing the ResultHandles for wrfmp,
                wrfout and clouds part of the dataset.

        """
        query = self._get_query(domain, mp_id)
        query = query.filter(
            Dataset.start_time >= start_time
            ).filter(
            Dataset.end_time <= end_time
            )
        query = query.order_by(Dataset.start_time.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time, domain=None, mp_id=None):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Start time of data slice [UTC].
            domain (str): Name of the domain.
            mp_id (int): ID of a microphysics scheme to be returned.

        Returns:
            dict:
                Dictionary containing the ResultHandles for wrfmp, wrfout and
                    clouds part of the dataset.

        """
        query = self._get_query(domain, mp_id)
        closest_start = get_closest(query, Dataset.start_time, time)
        closest_end = get_closest(query, Dataset.end_time, time)
        start_dif = abs(closest_start.start_time - time)
        end_dif = abs(closest_end.end_time - time)

        if start_dif < end_dif:
            return self._return_data(closest_start)
        else:
            return self._return_data(closest_end)

    def get_latest_data(self, domain=None, mp_id=None, n=1):
        """Find latest data

        Args:
            domain (str): Name of the domain.
            mp_id (int): ID of a microphysics scheme to be returned.
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of dictionaries containing the ResultHandles for wrfmp,
                wrfout and clouds part of the dataset. Corresponds to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """
        query = self._get_query(domain, mp_id)
        query = query.order_by(Dataset.start_time.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        """Update the data base with missing data

        Args:
            recheck (Bool): Whether to check data base for changed files.

        Raises:
            AssertionError: If more than 1 data set is found for the same
                time step.

        """
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                # Check for correct file names
                if file.startswith("clouds"):
                    file_type_name = "clouds"
                elif file.startswith("wrfmp"):
                    file_type_name = "wrfmp"
                elif file.startswith("wrfout"):
                    file_type_name = "wrfout"
                else:
                    print("Not a valid data file: ", file_path)
                    continue

                file_split = file.split("_")
                date_str = str(file_split[2])
                time_str = str(file_split[3])
                try:
                    dt.datetime.strptime(date_str + "_" + time_str,
                                         "%Y-%m-%d_%H%M%S")
                except ValueError:
                    print("File " + file_path + " does not match the file "
                          "name requested file name format: %Y-%m-%d_%H%M%S. "
                          "Skipping this file")
                    continue

                # Check if data file has an entry already
                if file_path in available_filenames:
                    if recheck is False:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                # Create new data file
                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == file_type_name).one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                wrf_data = self._handler.load_data(file_path)

                # Get domain
                x_res, y_res = wrf_data.DX, wrf_data.DY
                lon_0, lat_0 = wrf_data.CEN_LON, wrf_data.CEN_LAT
                lon_0 = np.round(float(lon_0), decimals=6)
                lat_0 = np.round(float(lat_0), decimals=6)

                # Get mp and time
                wrf_mp = int(wrf_data.MP_PHYSICS)
                start_time = dt.datetime.strptime(
                    str(wrf_data.Time.values[0]), "%Y-%m-%dT%H:%M:%S.%f000"
                    )
                end_time = dt.datetime.strptime(
                    str(wrf_data.Time.values[-1]), "%Y-%m-%dT%H:%M:%S.%f000"
                    )
                domain = self._session.query(Domain).filter(
                    Domain.x_res == x_res).filter(
                    Domain.y_res == y_res).filter(
                    Domain.lon_0 == lon_0).filter(
                    Domain.lat_0 == lat_0).one()
                mp_scheme = self._session.query(MPScheme).filter(
                    MPScheme.id == wrf_mp
                    ).one()

                # Get dataset
                existing_dataset = self._session.query(Dataset).filter(
                    Dataset.start_time == start_time).filter(
                    Dataset.end_time == end_time).filter(
                    Dataset.mp == mp_scheme).filter(
                    Dataset.domain == domain).filter(
                    Dataset.model_id == self.model.id
                    ).all()

                # Dataset entry
                if len(existing_dataset) == 0:
                    dataset = Dataset(start_time=start_time, end_time=end_time,
                                      domain=domain, mp=mp_scheme,
                                      model=self.model)

                    model_data = ModelData()
                elif len(existing_dataset) == 1:
                    dataset = existing_dataset[0]
                    model_data = self._session.query(ModelData).filter(
                        ModelData.dataset == dataset).one()
                else:
                    raise AssertionError("Length of dataset must be 0 or 1")
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


class CRSIMDataBase(DataBase):
    """Data base of CR-SIM data

    This class serves as an API to access the CR-SIM data. For documentation of
    initialization and general DataBase methods, see super class.


    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._handler = CRSIMDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result. This method
        is intended to be internal and should not be called by the user
        directly.

        Args:
            query (CRSIMData): Query result.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        attrs = {'file_path': query.file_path, 'time': query.time,
                 'mp': query.mp_id, 'radar': query.radar.name,
                 'hm': query.hm.name}
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(attrs['file_path'])
            )
        return data_handle

    def _get_query(self, mp_id=None, radar=None, hm="all"):
        """Returns the basic query with given input parameters

        Args:
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            hm (str): Name of simulated hydrometeor class.

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(CRSIMData)
        if mp_id:
            query = query.filter(CRSIMData.mp_id == int(mp_id))
        if hm:
            hm_id = self._session.query(Hydrometeor).filter(
                Hydrometeor.name == hm
                ).one().id
            query = query.filter(CRSIMData.hm_id == hm_id)
        if radar:
            radar_id = self._session.query(Radar).filter(
                Radar.name == radar
                ).one().id
            query = query.filter(CRSIMData.radar_id == radar_id)
        return query

    def get_data(self, start_time, end_time, mp_id=None, radar=None, hm="all"):
        """Gets data in given time range

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            hm (str): Name of simulated hydrometeor class.

        Returns:
            list:
                List of :meth:`ResultHandle` objects, one for each data file.

        """
        query = self._get_query(mp_id, radar, hm)
        query = query.filter(
            CRSIMData.time <= end_time
            ).filter(
            CRSIMData.time >= start_time
            )
        query = query.order_by(CRSIMData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time, mp_id=None, radar=None, hm="all"):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest data is
                returned.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            hm (str): Name of simulated hydrometeor class.

        Returns:
            ResultHandle:
                Container for the corresponding data slice.

        """
        query = self._get_query(mp_id, radar, hm)
        closest = get_closest(query, CRSIMData.time, time)
        return self._return_data(closest)

    def get_latest_data(self, mp_id=None, radar=None, hm="all", n=1):
        """Find latest data

        Args:
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            hm (str): Name of simulated hydrometeor class.
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of :meth:`ResultHandle` objects that correspond to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """
        query = self._get_query(mp_id, radar, hm)
        query = query.order_by(CRSIMData.time.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".nc"):
                    continue

                if file_path in available_filenames:
                    if not recheck:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "nc").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                data = self._handler.load_data(file_path)
                mp_id = int(data.MP_PHYSICS)
                radar_name = data.radar
                hm_name = data.hydrometeor
                time = dt.datetime.strptime(str(data['time'].values),
                                            "%Y-%m-%dT%H:%M:%S.%f000")

                # Query corresponding data base entries
                mp_scheme = self._session.query(MPScheme).filter(
                    MPScheme.id == mp_id
                    ).one()
                radar = self._session.query(Radar).filter(
                    Radar.name == radar_name
                    ).one()
                hm = self._session.query(Hydrometeor).filter(
                    Hydrometeor.name == hm_name
                    ).one()

                # Find if data entry exists already
                crsim_data = self._session.query(CRSIMData).filter(
                        CRSIMData.file_path == file_path
                        ).all()

                if len(crsim_data) == 1:
                    crsim_data[0].time = time
                    crsim_data[0].mp = mp_scheme
                    crsim_data[0].radar = radar
                    crsim_data[0].hm = hm

                if len(crsim_data) == 0:
                    new_entry = CRSIMData(file_path=file_path, time=time,
                                          mp=mp_scheme, radar=radar, hm=hm)
                    self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class RFDataBase(DataBase):
    """Data base of radar filter data

    The CR-SIM data is transformed from a Cartesian to a spherical grid with
    the radar filter. This class serves as an API to access this radar filter
    data. For documentation of initialization and general DataBase classes, see
    super class.

    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._handler = RFDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result. This method
        is intended to be internal and should not be called by the user
        directly.

        Args:
             query (RFData): Query result.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        attrs = {'file_path': query.file_path, 'time': query.time,
                 'mp': query.mp_id, 'radar': query.radar.name}
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(attrs['file_path'])
            )
        return data_handle

    def _get_query(self, mp_id=None, radar=None):
        """Returns the basic query with given input parameters

        Args:
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(RFData)
        if mp_id:
            query = query.filter(RFData.mp_id == int(mp_id))
        if radar:
            radar_id = self._session.query(Radar).filter(
                Radar.name == radar
                ).one().id
            query = query.filter(RFData.radar_id == radar_id)
        return query

    def get_data(self, start_time, end_time, mp_id=None, radar=None):
        """Gets data in given time range

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            list:
                List of :meth:`ResultHandle` objects, one for each data file.

        """
        query = self._get_query(mp_id, radar)
        query = query.filter(
            RFData.time >= start_time
            ).filter(
            RFData.time <= end_time
            )
        query = query.order_by(RFData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time, mp_id=None, radar=None):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest data is
                returned.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            ResultHandle:
                Container for the corresponding data slice.

        """
        query = self._get_query(mp_id, radar, )
        closest = get_closest(query, RFData.time, time)
        return self._return_data(closest)

    def get_latest_data(self, mp_id=None, radar=None, n=1):
        """Find latest data

        Args:
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of :meth:`ResultHandle` objects that correspond to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """
        query = self._get_query(mp_id, radar)
        query = query.order_by(RFData.time.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".nc"):
                    continue

                if file_path in available_filenames:
                    if not recheck:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "nc").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                rf_data = self._handler.load_data(file_path)
                time = rf_data.time.values
                rf_time = dt.datetime.strptime(str(time),
                                               "%Y-%m-%dT%H:%M:%S.%f000")
                mp_id = int(rf_data.MP_PHYSICS)
                radar_name = rf_data.radar

                # Query corresponding data base entries
                mp_scheme = self._session.query(MPScheme).filter(
                    MPScheme.id == mp_id
                    ).one()
                radar = self._session.query(Radar).filter(
                    Radar.name == radar_name
                    ).one()

                # Find if data entry exists already
                rf_data = self._session.query(RFData).filter(
                    RFData.file_path == file_path
                    ).all()

                if len(rf_data) == 1:
                    rf_data[0].time = rf_time
                    rf_data[0].mp_scheme = mp_scheme
                    rf_data[0].radar = radar

                if len(rf_data) == 0:
                    # Make new entry
                    new_entry = RFData(file_path=file_path, time=rf_time,
                                       mp=mp_scheme, radar=radar)
                    self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class RGDataBase(DataBase):
    """Data base of regular grid data

    Interpolating CR-SIM or DWD data to a regular Cartesian grid is a common
    task. To not have to repeat it at ech plotting script, the interpolation to
    the regular grid is done once and saved. This class serves as an API to
    access this data. For documentation of initialization and general DataBase
    classes, see super class.

    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._handler = RGDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result. This method
        is intended to be internal and should not be called by the user
        directly.

        Args:
            query (RGData): Query result.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        attrs = {'file_path': query.file_path, 'time': query.time,
                 'source': query.source, 'mp': query.mp_id,
                 'radar': query.radar.name}
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(attrs['file_path'])
            )
        return data_handle

    def _get_query(self, source=None, mp_id=None, radar=None):
        """Returns the basic query with given input parameters

        Args:
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(RGData)
        if source:
            query = query.filter(RGData.source == source)
        if mp_id:
            query = query.filter(RGData.mp_id == int(mp_id))
        if radar:
            radar_id = self._session.query(Radar).filter(
                Radar.name == radar
                ).one().id
            query = query.filter(RGData.radar_id == radar_id)
        return query

    def get_data(self, start_time, end_time, source=None, mp_id=None,
                 radar=None):
        """Gets data in given time range

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            list:
                List of :meth:`ResultHandle` objects, one for each data file.

        """
        query = self._get_query(source, mp_id, radar)
        query = query.filter(
            RGData.time <= end_time
            ).filter(
            RGData.time >= start_time
            )
        query = query.order_by(RGData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time, source=None, mp_id=None, radar=None):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest data is
                returned.
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            ResultHandle:
                Container for the corresponding data slice.

        """
        query = self._get_query(source, mp_id, radar)
        closest = get_closest(query, RGData.time, time)
        return self._return_data(closest)

    def get_latest_data(self, source=None, mp_id=None, radar=None, n=1):
        """Find latest data

        Args:
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of :meth:`ResultHandle` objects that correspond to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """
        query = self._get_query(source, mp_id, radar)
        query = query.order_by(RGData.time.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".nc"):
                    continue

                if file_path in available_filenames:
                    if not recheck:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "nc").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)

                # Load data
                data = self._handler.load_data(file_path)
                time = dt.datetime.strptime(str(data.attrs['time']),
                                            "%Y-%m-%d %H:%M:%S")

                # Query corresponding data base entries
                source = data.source
                try:
                    mp_scheme = self._session.query(MPScheme).filter(
                        MPScheme.id == int(data.MP_PHYSICS)
                        ).one()
                except AttributeError:
                    mp_scheme = None
                radar = self._session.query(Radar).filter(
                    Radar.name == data.radar
                    ).one()

                # Find if data entry exists already
                existing_data = self._session.query(RGData).filter(
                    RGData.file_path == file_path
                    ).all()

                if len(existing_data) == 1:
                    existing_data[0].time = time
                    existing_data[0].source = source
                    existing_data[0].mp = mp_scheme
                    existing_data[0].radar = radar

                if len(existing_data) == 0:
                    # Make new entry
                    new_entry = RGData(file_path=file_path, time=time,
                                       source=source, mp=mp_scheme, radar=radar)
                    self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class TracksDataBase(DataBase):
    """Data base of cell tracks data

    Using TINT, dataframes of cell tracks can be calculated. To avoid repeated
    calculations of the same cell tracks, this class serves as a data base to
    access the cell tracks data frames. For documentation of initialization and
    general DataBase methods, see super class.

    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._handler = TracksDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result. This method
        is intended to be internal and should not be called by the user
        directly.

        Args:
             query (TracksData): Query result.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        attrs = {'file_path': query.file_path, 'date': query.date,
                 'source': query.source, 'mp': query.mp_id,
                 'radar': query.radar.name}
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(attrs['file_path'])
            )
        return data_handle

    def _get_query(self, source=None, mp_id=None, radar=None):
        """Returns the basic query with given input parameters

        Args:
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(TracksData)

        if source:
            query = query.filter(TracksData.source == source)
        if mp_id:
            query = query.filter(TracksData.mp_id == int(mp_id))
        if radar:
            radar_id = self._session.query(Radar).filter(
                Radar.name == radar
                ).one().id
            query = query.filter(TracksData.radar_id == radar_id)
        return query

    def get_data(self, start_time, end_time, source=None, mp_id=None,
                 radar=None):
        """Gets data in given time range

        Args:
            start_time (datetime.datetime): Start time of data slice [UTC].
            end_time (datetime.datetime): End time of data slice [UTC].
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            list:
                List of :meth:`ResultHandle` objects, one for each data file.

        """
        start_date = dt.datetime(start_time.year, start_time.month,
                                 start_time.day)
        end_date = dt.datetime(end_time.year, end_time.month, end_time.day)
        query = self._get_query(source, mp_id, radar)
        query = query.filter(
            TracksData.date >= start_date).filter(
            TracksData.date <= end_date
            )
        query = query.order_by(TracksData.date.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time, source=None, mp_id=None, radar=None):
        """Get closest data

        Given a date time input, this method will return the data set
        closest to this time.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest data is
                returned.
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.

        Returns:
            ResultHandle:
                Container for the corresponding data slice.

        """
        query = self._get_query(source, mp_id, radar)
        closest = get_closest(query, TracksData.date, time)
        return self._return_data(closest)

    def get_latest_data(self, source=None, mp_id=None, radar=None, n=1):
        """Find latest data

        Args:
            source (str): Whether the data comes from DWD or MODEL data.
            mp_id (int): WRF ID of a microphysics scheme to be returned.
            radar (str): Name of simulated radar.
            n (int): Number of latest data files to be returned.

        Returns:
            list:
                List of :meth:`ResultHandle` objects that correspond to the
                latest 'n' data files. Ordered in a way so that the first entry
                corresponds to the latest data file.

        """

        query = self._get_query(source, mp_id, radar)
        query = query.order_by(TracksData.date.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".pkl"):
                    continue

                if file_path in available_filenames:
                    if not recheck:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "nc").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)

                # Load data
                data = self._handler.load_data(file_path)
                date = dt.datetime.strptime(data.date, "%Y-%m-%d")

                # Query corresponding data base entries
                source = data.source
                try:
                    mp_scheme = self._session.query(MPScheme).filter(
                        MPScheme.id == int(data.MP_PHYSICS)
                        ).one()
                except AttributeError:
                    mp_scheme = None
                radar = self._session.query(Radar).filter(
                    Radar.name == data.radar
                    ).one()

                # Find if data entry exists already
                existing_data = self._session.query(TracksData).filter(
                    TracksData.file_path == file_path
                    ).all()

                if len(existing_data) == 1:
                    existing_data[0].date = date
                    existing_data[0].source = source
                    existing_data[0].mp_scheme = mp_scheme
                    existing_data[0].radar = radar

                if len(existing_data) == 0:
                    # Make new entry
                    new_entry = TracksData(file_path=file_path, date=date,
                                           source=source, mp=mp_scheme,
                                           radar=radar)
                    self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class RadarDataBase(DataBase):
    """Abstract radar data base

    This is the main radar data class for interaction with a user. This class
    is abstract, that means is has actually no implemented methods. All methods
    are specifically implemented within the corresponding subclasses
    :class:`MiraRadarDataBase` and :class:`PoldiRadarDataBase`.
    For documentation of initialization and general DataBase methods, see super
    class.

    The following methods are available to all subclasses:

        - :meth:`get_closest_rhi`:
            Finds the closest rhi to an input datetime.

    """
    def get_closest_rhi(self, time):
        """Find the closest RHI in time

        Finds the closest RHI to the given datetime within the database.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest RHI is
                returned.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        raise NotImplementedError

    def get_closest_ppi(self, time):
        """Find the closest PPI in time

        Finds the closest PPI to the given datetime within the database.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest PPI is
                returned.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        raise NotImplementedError

    def get_data(self, start_time, end_time):
        raise NotImplementedError

    def get_closest_data(self, time):
        raise NotImplementedError

    def get_latest_data(self, n=1):
        raise NotImplementedError

    def update_db(self, recheck=True):
        raise NotImplementedError


class DWDDataBase(RadarDataBase):
    """Radar data base of DWD volume data.

    This class serves as an API to access DWD data. For documentation of
    initialization and general DataBase methods, see super class.

    """
    def __init__(self, data_path, db, update=True, recheck=True):
        self._data_path = data_path
        self._handler = DWDDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        """Return the result handle

        Returns the corresponding ResultHandle to the query result.

        Args:
            query (DWDData): Query result.

        Returns:
            ResultHandle:
                To query result corresponding ResultHandle.

        """
        attrs = {'file_path': query.file_path, 'time': query.time}
        data_handle = ResultHandle(
            attrs,
            lambda: self._handler.load_data(attrs['file_path']))
        return data_handle

    def _get_query(self):
        """Returns the basic query with given input parameters

        Returns:
            query:
                The sql query.

        """
        query = self._session.query(DWDData)
        return query

    def get_closest_rhi(self, time):
        raise NotImplementedError

    def get_closest_ppi(self, time):
        raise NotImplementedError

    def get_data(self, start_time, end_time):
        query = self._get_query()
        query = query.filter(
            DWDData.time >= start_time
            ).filter(
            DWDData.time <= end_time
            )
        query = query.order_by(DWDData.time.asc())
        return list(map(self._return_data, query.all()))

    def get_closest_data(self, time):
        query = self._get_query()
        closest = get_closest(query, DWDData.time, time)
        return self._return_data(closest)

    def get_latest_data(self, n=1):
        query = self._get_query()
        query = query.order_by(DWDData.time.desc()).limit(n)
        return list(map(self._return_data, query.all()))

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                if not file_path.endswith(".hd5"):
                    continue
                if file_path.endswith("20190528.hd5"):  # Wrong file in archive
                    continue

                if file_path in available_filenames:
                    if recheck is False:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                # Create new data file
                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "hdf5").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                scan_data = self._handler.load_data(file_path)
                time = dt.datetime.strptime(str(scan_data['time']),
                                            "%Y-%m-%d %H:%M:%S")

                # Find if data entry exists already
                dwd_data = self._session.query(DWDData).filter(
                    DWDData.file_path == file_path
                    ).all()
                if len(dwd_data) == 1:
                    dwd_data[0].time = time

                if len(dwd_data) == 0:
                    new_entry = DWDData(file_path=file_path, time=time)
                    self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class MiraDataBase(RadarDataBase):
    """Radar data base of Mira-35

    Specific subclass of :class:`RadarDataBase`: for data of Mira-35.
    This class serves as an API to access Mira-35 data. For documentation of
    initialization and general DataBase methods, see super classes.

    The following extra methods are available:

        - :meth:`get_rhis`:
            Finds all rhis within the given start- and end-time.

    """
    def __init__(self, data_path, db, recheck=True, update=True):
        self._data_path = data_path
        self._handler = MiraDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        self.radar = self._session.query(Radar).filter(
            Radar.name == "Mira35"
            ).one()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        attrs = {'dataset_id': query.dataset.id,
                 'start_time': query.start_time, 'end_time': query.end_time,
                 'resolution': query.resolution}
        if query.__tablename__ == "rhi_data":
            attrs['azimuth'] = query.azimuth

        try:
            mmclx_file = query.dataset.mmclx_file.filename
        except AttributeError:
            mmclx_file = None
        try:
            nc_file = query.dataset.nc_file.filename
        except AttributeError:
            nc_file = None

        loaded_dataset = {'mmclx_file': mmclx_file, 'nc_file': nc_file}
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(
                loaded_dataset, query.start_time, query.end_time
                )
            )
        return data_handle

    def get_rhis(self, start_time, end_time):
        """Finds all RHI scans in given time range

        Args:
            start_time (datetime.datetime): Start time to search the database.
            end_time (datetime.datetime): End time to search the database.

        Returns:
            list:
                List of :meth:`ResultHandle` objects, one for each RHI.

        """
        query = self._session.query(RHIData).filter(
            RHIData.radar == self.radar
            ).filter(
            RHIData.start_time >= start_time
            ).filter(
            RHIData.end_time <= end_time
            )
        return list(map(self._return_data, query.all()))

    def get_closest_rhi(self, time):
        query = self._session.query(RHIData).filter(
            RHIData.radar == self.radar
            )
        closest = get_closest(query, RHIData.start_time, time)
        return self._return_data(closest)

    def get_closest_ppi(self, time):
        query = self._session.query(PPIData).filter(
            PPIData.radar == self.radar
            )
        closest = get_closest(query, PPIData.start_time, time)
        return self._return_data(closest)

    def get_data(self, start_time, end_time):
        raise NotImplementedError

    def get_closest_data(self, time):
        raise NotImplementedError

    def get_latest_data(self, n=1):
        raise NotImplementedError

    def update_db(self, recheck=True):
        """Update the data base with missing data

        Args:
            recheck (Bool): Whether to check data base for changed files.

        Raises:
            AssertionError: If more than 1 data set is found for the same
                time step.

        """
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Loop through all files
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                # Get the file name without the ending and create dataset dict
                dataset_dict = {'mmclx_file': "", 'nc_file': ""}
                if file_path.endswith('nc'):
                    dataset_dict['nc_file'] = file_path
                    file_type_name = "nc"
                elif file_path.endswith("mmclx"):
                    file_type_name = "mmclx"
                    dataset_dict['mmclx_file'] = file_path
                else:
                    print("Not a valid data file: ", file_path)
                    continue

                # Check if data file has an entry already
                if file_path in available_filenames:
                    if not recheck:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()

                # Create new data file / dataset
                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == file_type_name).one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                mira_data = self._handler.load_data(dataset_dict)
                res = mira_data['range'][1] - mira_data['range'][0]

                # Get dataset
                data_start = mira_data.times.values[0]
                data_start = dt.datetime.strptime(str(data_start),
                                                  "%Y-%m-%dT%H:%M:%S.%f000")
                data_end = mira_data.times.values[-1]
                data_end = dt.datetime.strptime(str(data_end),
                                                "%Y-%m-%dT%H:%M:%S.%f000")
                existing_dataset = self._session.query(Dataset).filter(
                    Dataset.start_time == data_start).filter(
                    Dataset.end_time == data_end).all()
                if len(existing_dataset) == 0:
                    dataset = Dataset(start_time=data_start, end_time=data_end)
                    if file_type_name == "nc":
                        dataset.nc_file = data_file
                    elif file_type_name == "mmclx":
                        dataset.mmclx_file = data_file
                    self._session.add(dataset)
                elif len(existing_dataset) == 1:
                    dataset = existing_dataset[0]
                    if file_type_name == "nc":
                        dataset.nc_file = data_file
                    elif file_type_name == "mmclx":
                        dataset.mmclx_file = data_file
                else:
                    raise AssertionError("Length of dataset must be 0 or 1")

                rhi_scans = self._handler.find_rhi_sweeps(mira_data)
                ppi_scans = self._handler.find_ppi_sweeps(mira_data)

                # Check if any scan was found
                if len(ppi_scans) == 0 and len(rhi_scans) == 0:
                    self._session.commit()
                    continue

                # Make entry for each PPI scan
                for ppi in ppi_scans:
                    ppi_data = mira_data.isel(time=ppi)
                    ele = ppi_data.elv.mean(axis=0)
                    start_time = dt.datetime.strptime(
                        str(ppi_data.times.values[0]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)
                    end_time = dt.datetime.strptime(
                        str(ppi_data.times.values[-1]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)

                    # Find if scan exists already
                    scans = self._session.query(PPIData).filter(
                        PPIData.radar == self.radar
                        ).filter(
                        PPIData.start_time == start_time
                        ).all()

                    # Update scan data
                    if len(scans) == 1:
                        scan = scans[0]
                        scan.start_time = start_time
                        scan.end_time = end_time
                        scan.elevation = ele
                        scan.resolution = res
                        scan.radar = self.radar
                        scan.dataset = dataset

                    # Create new scan data
                    elif len(scans) == 0:
                        scan = PPIData(start_time=start_time, end_time=end_time,
                                       elevation=ele, radar=self.radar,
                                       dataset=dataset, resolution=res)
                        self._session.add(scan)

                # Make entry for each RHI scan
                for rhi in rhi_scans:
                    rhi_data = mira_data.isel(time=rhi)
                    azi = rhi_data.az.mean(axis=0)
                    start_time = dt.datetime.strptime(
                        str(rhi_data.times.values[0]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)
                    end_time = dt.datetime.strptime(
                        str(rhi_data.times.values[-1]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)

                    # Find if scan exists already
                    scan = self._session.query(RHIData).filter(
                        RHIData.radar == self.radar
                        ).filter(
                        RHIData.start_time == start_time
                        ).all()

                    # Update scan data
                    if len(scan) == 1:
                        scan[0].start_time = start_time
                        scan[0].end_time = end_time
                        scan[0].elevation = azi
                        scan[0].resolution = res
                        scan[0].radar = self.radar
                        scan[0].dataset = dataset

                    # Create new scan data
                    elif len(scan) == 0:
                        new_entry = RHIData(start_time=start_time,
                                            end_time=end_time,
                                            azimuth=azi, radar=self.radar,
                                            dataset=dataset, resolution=res)
                        self._session.add(new_entry)
                self._session.commit()
        self._session.commit()


class PoldiDataBase(RadarDataBase):
    """Radar data base of Poldirad

    Specific subclass of :class:`RadarDataBase`: for data of Poldirad. This
    class serves as an API to access Poldirad data. For documentation of
    initialization and general DataBase methods, see super classes.

    The following extra methods are available:

        - :meth:`get_closest_srhi`:
            Finds the closest sector rhi to an input datetime.

    """
    def __init__(self, data_path, db, recheck=True, update=True):
        self._data_path = data_path
        self._handler = PoldiDataHandler()
        self._db = "sqlite:///" + db
        self._recheck = recheck
        self._update = update
        if not os.path.exists(db):
            create_db(db)

    def __enter__(self):
        engine = create_engine(self._db)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._session = sessionmaker(bind=engine)()
        self.radar = self._session.query(Radar).filter(
            Radar.name == "Poldirad"
            ).one()
        if self._update:
            self.update_db(self._recheck)
        return self

    def __exit__(self, *args):
        self._session.close()

    def _return_data(self, query):
        attrs = {'file_path': query.dataset.hdf5_file.filename,
                 'start_time': query.start_time, 'end_time': query.end_time,
                 'resolution': query.resolution}
        if query.__tablename__ == "rhi_data":
            attrs['azimuth'] = query.azimuth
        if query.__tablename__ == "ppi_data":
            attrs['elevation'] = query.elevation
        scan_number = query.scan_number
        data_handle = ResultHandle(
            attrs, lambda: self._handler.load_data(attrs['file_path'],
                                                   scan=scan_number)
            )
        return data_handle

    def get_closest_rhi(self, time):
        query = self._session.query(RHIData).filter(
            RHIData.radar == self.radar
            )
        closest = get_closest(query, RHIData.start_time, time)
        return self._return_data(closest)

    def get_closest_ppi(self, time):
        query = self._session.query(PPIData).filter(
            PPIData.radar == self.radar
            )
        closest = get_closest(query, PPIData.start_time, time)
        return self._return_data(closest)

    def get_closest_srhi(self, time):
        """Get closest Sector RHI

        Finds the closest Sector RHI to the given datetime within the database.

        Args:
            time (datetime.datetime): Time [UTC], to which the closest
                Sector RHI is returned.

        Returns:
            list:
                All RHI Resulthandles corresponding to the SRHI.

        """
        query = self._session.query(SRHIData).filter(
            SRHIData.radar == self.radar
            )
        closest = get_closest(query, SRHIData.start_time, time)
        rhis = closest.rhi_data
        return list(map(self._return_data, rhis))

    def get_data(self, start_time, end_time):
        raise NotImplementedError

    def get_closest_data(self, time):
        raise NotImplementedError

    def get_latest_data(self, n=1):
        raise NotImplementedError

    def update_db(self, recheck=True):
        available_files = self._session.query(Datafile).all()
        available_filenames = [x.filename for x in available_files]

        # Add missing data to json file
        for subdir, dirs, files in os.walk(self._data_path):
            for file in sorted(files):
                file_path = subdir + os.sep + file
                file_path = os.path.normpath(file_path)

                # Only hdf5 files can be read
                if not file_path.endswith("hdf5"):
                    continue

                # Check if data file has an entry already
                if file_path in available_filenames:
                    if recheck is False:
                        continue

                    # Check if file needs recheck
                    data_file = self._session.query(Datafile).filter(
                        Datafile.filename == file_path).one()
                    last_checked = data_file.last_checked
                    checked_ts = dt.datetime.timestamp(last_checked)
                    filedate = dt.datetime.utcfromtimestamp(
                        os.path.getmtime(file_path)
                        )
                    file_ts = dt.datetime.timestamp(filedate)
                    if file_ts < checked_ts:
                        continue
                    else:
                        data_file.last_checked = dt.datetime.utcnow()
                        dataset = data_file.hdf5_dataset[0]

                # Create new data file
                else:
                    # Data file entry
                    file_type = self._session.query(FileType).filter(
                        FileType.name == "hdf5").one()
                    data_file = Datafile(filename=file_path,
                                         file_type_id=file_type.id,
                                         last_checked=dt.datetime.utcnow())
                    self._session.add(data_file)

                    # Create a new dataset
                    dataset = Dataset(hdf5_file=data_file)
                    self._session.add(dataset)

                # Print some output to make clear that data is loaded
                print("Updating: ", file_path)
                poldi_data = self._handler.load_data(file_path)

                if not poldi_data:
                    corrupt_type = self._session.query(FileType).filter(
                        FileType.name == "corrupt").one()
                    data_file.file_type = corrupt_type
                    continue

                # If HV-Volume data
                if poldi_data.task == "HV-Volumen" \
                        or poldi_data.task == "Volumen":
                    start_time = dt.datetime.strptime(
                        str(poldi_data.time_start.values),
                        "%Y-%m-%dT%H:%M:%S.%f000"
                        )
                    end_time = dt.datetime.strptime(
                        str(poldi_data.time_end.values),
                        "%Y-%m-%dT%H:%M:%S.%f000"
                        )
                    new_entry = HVData(
                        start_time=start_time, end_time=end_time,
                        radar=self.radar, dataset=dataset
                        )
                    self._session.add(new_entry)
                    continue

                sector_rhi = []
                for scan_nr in np.arange(poldi_data.dims['scan_number']):
                    ds = poldi_data.isel(scan_number=scan_nr)
                    times = ds.times.values[ds.times.notnull()]

                    # Get time of scan
                    start_time = dt.datetime.strptime(
                        str(times[0]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)
                    end_time = dt.datetime.strptime(str(
                        times[-1]),
                        "%Y-%m-%dT%H:%M:%S.%f000").replace(microsecond=0)
                    res = ds.attrs["Resolution"]

                    # If PPI data
                    if ds.task == "PPI":
                        mean_elv = ds.elv.mean(axis=0)
                        elv = np.round(float(mean_elv), 2)

                        # Find if scan exists already
                        scan = self._session.query(PPIData).filter(
                            PPIData.radar == self.radar
                            ).filter(
                            PPIData.start_time == start_time
                            ).all()

                        # Update scan data
                        if len(scan) == 1:
                            scan[0].start_time = start_time
                            scan[0].end_time = end_time
                            scan[0].elevation = elv
                            scan[0].resolution = res
                            scan[0].radar = self.radar
                            scan[0].dataset = dataset

                        elif len(scan) == 0:
                            new_entry = PPIData(start_time=start_time,
                                                end_time=end_time,
                                                radar=self.radar, elevation=elv,
                                                dataset=dataset, resolution=res)
                            self._session.add(new_entry)

                    # If RHI data
                    if ds.task == "RHI":
                        mean_azi = ds.az.mean(axis=0)
                        azi = np.round(float(mean_azi), 2)

                        # Find if scan exists already
                        scans = self._session.query(RHIData).filter(
                            RHIData.radar == self.radar
                            ).filter(
                            RHIData.start_time == start_time
                            ).all()

                        # Update scan data
                        if len(scans) == 1:
                            scan = scans[0]
                            scan.start_time = start_time
                            scan.end_time = end_time
                            scan.azimuth = azi
                            scan.resolution = res
                            scan.radar = self.radar
                            scan.dataset = dataset
                            scan.scan_number = int(scan_nr)

                        elif len(scans) == 0:
                            scan = RHIData(start_time=start_time,
                                           end_time=end_time, radar=self.radar,
                                           azimuth=azi, dataset=dataset,
                                           resolution=res,
                                           scan_number=int(scan_nr))
                            self._session.add(scan)
                        else:
                            raise AssertionError("Found more than 1 RHI scan "
                                                 "with the same start time")
                        sector_rhi.append(scan)

                # Sector RHI part
                if len(sector_rhi) < 2:  # Sector RHI must have at least 2 RHIs
                    self._session.commit()
                    continue
                sector_start_time = sector_rhi[0].start_time
                sector_end_time = sector_rhi[-1].end_time

                # Find if Sector RHI exists already
                sector_scans = self._session.query(SRHIData).filter(
                    SRHIData.radar == self.radar).filter(
                    SRHIData.start_time == sector_start_time
                    ).all()

                # Update scan data
                if len(sector_scans) == 1:
                    sector_scan = sector_scans[0]
                    sector_scan.start_time = sector_start_time
                    sector_scan.end_time = sector_end_time
                    sector_scan.radar = self.radar

                # Create new scan data
                elif len(sector_scans) == 0:
                    sector_scan = SRHIData(start_time=sector_start_time,
                                           end_time=sector_end_time,
                                           radar=self.radar)
                    self._session.add(sector_scan)
                else:
                    raise AssertionError("Found more than 1 SRHI scan for the "
                                         "same start time")

                # Add all corresponding RHI scans to SRHI Data
                for rhi in sector_rhi:
                    rhi.sector_rhi = sector_scan
                self._session.commit()
        self._session.commit()
