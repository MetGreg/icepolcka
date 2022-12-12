"""SQLAlchemy tables

For my database, I make use of SQLAlchemy tables. In this module, these tables are defined.
All the classes are SQL based databases. The SQL tables are defined  in the 'tables' module using an
ORM-approach with SQLAlchemy. These classes are simply tables that define the columns of the SQL
table.


"""
import os

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, \
    create_engine
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from icepolcka_utils import utils

Base = declarative_base()


class FileType(Base):
    """SQL table for file types"""
    __tablename__ = "file_type"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of file type.


class Datafile(Base):
    """SQL table for all data files"""
    __tablename__ = "datafile"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    filename: String = Column(String)  #: Name of data file.
    #: ID of file type table row corresponding to the datafile row.
    file_type_id: Integer = Column(Integer, ForeignKey("file_type.id"))
    #: Relationship to FileType row corresponding to the datafile row.
    file_type: FileType = relationship(FileType, backref=backref("datafile", uselist=True))


class Model(Base):
    """SQL table for models"""
    __tablename__ = "model"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of the model.


class Domain(Base):
    """SQL table for WRF domains"""
    __tablename__ = "domain"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of the domain.
    x_res: Float = Column(Float)  #: Grid spacing in x direction (m).
    y_res: Float = Column(Float)  #: Grid spacing in y direction (m).
    lon_0: Float = Column(Float)  #: lon_0 from WRF settings (°).
    lat_0: Float = Column(Float)  #: lat_0 from WRF settings (°).
    x_dim: Float = Column(Integer)  #: Number of grid points in x direction.
    y_dim: Float = Column(Integer)  #: Number of grid points in y direction.
    z_dim: Float = Column(Integer)  #: Number of grid points in z direction.


class MPScheme(Base):
    """SQL table for WRF microphysics schemes"""
    __tablename__ = "mp_scheme"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of the MP scheme.


class Dataset(Base):
    """SQL table for datasets"""
    __tablename__ = "dataset"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    start_time: DateTime = Column(DateTime)  #: Start time (UTC) of Dataset.
    end_time: DateTime = Column(DateTime)  #: End time (UTC) of Dataset.
    #: ID of datafile table row corresponding to the nc file of the dataset row.
    nc_file_id: Integer = Column(Integer, ForeignKey("datafile.id"))
    #: Relationship to Datafile row corresponding to the nc file of the dataset row.
    nc_file: Datafile = relationship(Datafile, foreign_keys=[nc_file_id],
                                     backref=backref("nc_dataset", uselist=True))
    #: ID of datafile table row corresponding to the hdf5 file of the dataset row.
    hdf5_file_id: Integer = Column(Integer, ForeignKey("datafile.id"))
    #: Relationship to Datafile row corresponding to the hdf5 file of the dataset row.
    hdf5_file: Datafile = relationship(Datafile, foreign_keys=[hdf5_file_id],
                                       backref=backref("hdf5_dataset", uselist=True))
    #: ID of datafile table row corresponding to the wrf clouds file of the dataset row.
    clouds_file_id = Column(Integer, ForeignKey("datafile.id"))
    #: Relationship to Datafile row corresponding to the wrf clouds file of the dataset row.
    clouds_file = relationship(Datafile, foreign_keys=[clouds_file_id],
                               backref=backref("clouds_dataset", uselist=True))
    #: ID of datafile table row corresponding to the wrf mp file of the dataset row.
    wrfmp_file_id = Column(Integer, ForeignKey("datafile.id"))
    #: Relationship to Datafile row corresponding to the wrf mp file of the dataset row.
    wrfmp_file = relationship(Datafile, foreign_keys=[wrfmp_file_id],
                              backref=backref("wrfmp_dataset", uselist=True))
    #: ID of datafile table row corresponding to the wrfout file of the dataset row.
    wrfout_file_id = Column(Integer, ForeignKey("datafile.id"))
    #: Relationship to Datafile row corresponding to the wrfout file of the dataset row.
    wrfout_file = relationship(Datafile, foreign_keys=[wrfout_file_id],
                               backref=backref("wrfout_dataset", uselist=True))
    #: ID of datafile table row corresponding to the mp scheme of the dataset row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to Datafile row corresponding to the mp scheme of the dataset row.
    mp = relationship(MPScheme, backref=backref("mp_dataset", uselist=True))
    #: ID of Domain table row corresponding to the domain of the dataset row.
    domain_id = Column(Integer, ForeignKey("domain.id"))
    #: Relationship to Domain table row corresponding to the domain of the dataset row.
    domain = relationship(Domain, backref=backref("domain_dataset", uselist=True))
    #: ID of Model table row corresponding to the model of the dataset row.
    model_id = Column(Integer, ForeignKey("model.id"))
    #: Relationship to Model table row corresponding to the model of the dataset row.
    model = relationship(Model, backref=backref("model_dataset", uselist=True))


class Hydrometeor(Base):
    """SQL table for hydrometeor classes"""
    __tablename__ = "hydrometeor"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of the hydrometeor class


class Radar(Base):
    """SQL table for radars"""
    __tablename__ = "radar"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    name: String = Column(String)  #: Name of the radar.
    frequency: Float = Column(Float)  #: Radar frequency (GHz).
    height: Float = Column(Float)  #: Radar height above mean sea level (m).
    beamwidth: Float = Column(Float)  #: Radar half-power beamwidth (°).
    resolution: Float = Column(Float)  #: Radar range resolution (m).
    range: Float = Column(Float)  #: Radar maximum range (m).
    sensitivity: Float = Column(Float)  #: Radar sensitivity (dBZ).
    wrf_index_x: Integer = Column(Integer)  #: x-index of radar location in WRF Munich domain.
    wrf_index_y: Integer = Column(Integer)  #: y-index of radar location in WRF Munich domain.
    longitude: Float = Column(Float)  #: Radar site longitude (°).
    latitude: Float = Column(Float)  #: Radar site latitude (°).


class ModelData(Base):
    """SQL table for model data"""
    __tablename__ = "model_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    #: ID of Model table row corresponding to the model of the ModelData row.
    model_id = Column(Integer, ForeignKey("model.id"))
    #: Relationship to Model row corresponding to the model of the ModelData row.
    model = relationship(Model, backref=backref("model_data", uselist=True))
    #: ID of Dataset table row corresponding to the dataset of the ModelData row.
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    #: Relationship to Dataset table row corresponding to the dataset of the ModelData row.
    dataset = relationship(Dataset, backref=backref("model_data", uselist=True))


class CRSIMData(Base):
    """SQL table for CR-SIM data"""
    __tablename__ = "crsim_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to the CRSIM data file.
    time: DateTime = Column(DateTime)  #: Time stamp of CR-SIM data (UTC).
    #: ID of Radar table row corresponding to the radar of the CRSIMData row.
    radar_id = Column(Integer, ForeignKey("radar.id"))
    #: Relationship to Radar row corresponding to the radar of the CRSIMData row.
    radar = relationship(Radar, backref=backref("crsim_data", uselist=True))
    #: ID of MPScheme table row corresponding to the mp_scheme of the CRSIMData row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to MPScheme row corresponding to the mp_scheme of the CRSIMData row.
    mp = relationship(MPScheme, backref=backref("crsim_data", uselist=True))
    #: ID of Hydrometeor table row corresponding to the hydrometeor of the CRSIMData row.
    hm_id = Column(Integer, ForeignKey("hydrometeor.id"))
    #: Relationship to Hydrometeor row corresponding to the hydrometeor of the CRSIMData row.
    hm = relationship(Hydrometeor, backref=backref("crsim_data", uselist=True))


class RFData(Base):
    """SQL table for radarfilter data"""
    __tablename__ = "radar_filter_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to RF data file.
    time: DateTime = Column(DateTime)  #: Time stamp of RF data (UTC).
    #: ID of Radar table row corresponding to the radar of the RFData row.
    radar_id = Column(Integer, ForeignKey("radar.id"))
    #: Relationship to Radar row corresponding to the radar of the RFData row.
    radar = relationship(Radar, backref=backref("rf_data", uselist=True))
    #: ID of MPScheme table row corresponding to the mp_scheme of the RFData row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to MPScheme row corresponding to the mp_scheme of the RFData row.
    mp = relationship(MPScheme, backref=backref("rf_data", uselist=True))


class RGData(Base):
    """SQL table for data interpolated to the regular grid"""
    __tablename__ = "regular_grid_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to RG data file.
    time: DateTime = Column(DateTime)  #: Time stamp of RG data (UTC).
    source: String = Column(String)  #: Data source ('DWD' or 'MODEL').
    #: ID of Radar table row corresponding to the radar of the RGData row.
    radar_id = Column(Integer, ForeignKey("radar.id"))
    #: Relationship to Radar row corresponding to the radar of the RGData row.
    radar = relationship(Radar, backref=backref("regular_grid_data", uselist=True))
    #: ID of MPScheme table row corresponding to the mp_scheme of the RGData row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to MPScheme row corresponding to the mp_scheme of the RGData row.
    mp = relationship(MPScheme, backref=backref("regular_grid_data", uselist=True))


class HMCData(Base):
    """SQL table for hydrometeor classification data"""
    __tablename__ = "hydrometeor_classification_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to HMC data file.
    time: DateTime = Column(DateTime)  #: Time stamp of HMC data (UTC).
    source: String = Column(String)  #: Data source ('DWD' or 'MODEL').
    method: String = Column(String)  #: Name of the HMC method, e.g. 'Dolan'.
    #: ID of MPScheme table row corresponding to the mp_scheme of the HMCData row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to MPScheme row corresponding to the mp_scheme of the HMCData row.
    mp = relationship(MPScheme, backref=backref("hydrometeor_classification_data", uselist=True))


class TempData(Base):
    """SQL table for temperature data"""
    __tablename__ = "temperature_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to Temp data file.
    time: DateTime = Column(DateTime)  #: Time stamp of Temp data file (UTC).
    #: ID of MPScheme table row corresponding to the mp_scheme of the TempData row.
    mp_id = Column(Integer, ForeignKey("mp_scheme.id"))
    #: Relationship to MPScheme row corresponding to the mp_scheme of the TempData row.
    mp = relationship(MPScheme, backref=backref("temperature_data", uselist=True))


class DWDData(Base):
    """SQL table for DWD data"""
    __tablename__ = "dwd_data"
    id: Integer = Column(Integer, primary_key=True)  #: SQL row ID.
    file_path: String = Column(String)  #: Path to data file.
    time: DateTime = Column(DateTime)  #: Time stamp of DWD data file (UTC).


def create_session(db_path):
    """Create SQL session

    :param db_path: Path to database file.
    :type db_path: str

    Returns:
        ~sqlalchemy.orm.session.Session:
            The current session.

    """
    if not os.path.exists(db_path):
        folder_split = db_path.split(os.sep)[:-1]
        folder = os.sep.join(folder_split)
        utils.make_folder(folder)
    engine = create_engine("sqlite:///" + db_path)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    return session


def create_tables(db_path, session=None):
    """Create the basic database structure

    This should only be called when the database doesn't exist yet. The method adds basic table
    entries to the database. This includes all filetypes, models, domains, microphysics schemes,
    radars and hydrometeor classes used in the icepolcka_utils module.

    :param db_path: Path to database file.
    :type db_path: str
    :param session: Existing session. If None, a new session will be created.
    :type db_path: ~sqlalchemy.orm.session.Session

    Returns:
        ~sqlalchemy.orm.session.Session:
            The current session.

    """
    # If there is no database as input, one needs to be created
    if session is None:
        session = create_session(db_path)
    _add_file_types(session)
    _add_models(session)
    _add_domains(session)
    _add_schemes(session)
    _add_radars(session)
    _add_hydrometeors(session)
    session.commit()
    return session


def _add_file_types(session):
    # The names of the filetypes match the ending
    nc_file = FileType(name="nc")
    clouds_file = FileType(name="clouds")
    wrfmp_file = FileType(name="wrfmp")
    wrfout_file = FileType(name="wrfout")
    hdf5_file = FileType(name="hdf5")
    corrupt_file = FileType(name="corrupt")
    session.add_all([nc_file, clouds_file, wrfmp_file, wrfout_file, hdf5_file, corrupt_file])


def _add_models(session):
    # There is only one model currently used
    wrf = Model(name="WRF")
    session.add_all([wrf])


def _add_domains(session):
    # WRF domains used have specific characteristics that are defined here
    europe = Domain(name="Europe", x_res=10000, y_res=10000, lon_0=7.5, lat_0=50.000015, x_dim=374,
                    y_dim=374, z_dim=39)
    germany = Domain(name="Germany", x_res=2000, y_res=2000, lon_0=11.547821, lat_0=48.165325,
                     x_dim=220, y_dim=220, z_dim=39)
    munich = Domain(name="Munich", x_res=400, y_res=400, lon_0=11.574249, lat_0=48.145794,
                    x_dim=360, y_dim=360, z_dim=39)
    session.add_all([europe, germany, munich])


def _add_schemes(session):
    # Microphysics schemes have specific IDs. These are defined here
    thompson_scheme = MPScheme(id=8, name="Thompson")
    morrison_scheme = MPScheme(id=10, name="Morrison")
    thompson_aerosol_scheme = MPScheme(id=28, name="Thompson Aerosol Aware")
    sbm_scheme = MPScheme(id=30, name="Fast Spectral Bin")
    p3_scheme = MPScheme(id=50, name="P3")
    session.add_all([thompson_scheme, morrison_scheme, thompson_aerosol_scheme, sbm_scheme,
                     p3_scheme])


def _add_radars(session):
    # The radars used have specific characteristics that are defined here
    isen = Radar(name="Isen", frequency=5.5, height=678, beamwidth=1.0, sensitivity=-50,
                 longitude=12.101779, latitude=48.174705)
    session.add_all([isen])


def _add_hydrometeors(session):
    # The names of the hydrometeor classes equal the CR-SIM names
    cloud = Hydrometeor(name="cloud")
    ice = Hydrometeor(name="ice")
    rain = Hydrometeor(name="rain")
    snow = Hydrometeor(name="snow")
    graupel = Hydrometeor(name="graupel")
    parimedice = Hydrometeor(name="parimedice")
    smallice = Hydrometeor(name="smallice")
    unrimedice = Hydrometeor(name="unrimedice")
    all_hm = Hydrometeor(name="all")
    session.add_all([cloud, ice, rain, snow, graupel, parimedice, smallice, unrimedice, all_hm])

