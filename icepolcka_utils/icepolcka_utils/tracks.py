"""Cell tracking module

This module contains all classes specific to the cell tracking algorithms.
The logic behind the tracks module is very close to the TINT package
https://github.com/openradar/TINT


"""
import copy
import numpy as np
import pandas as pd

from tint.helpers import Counter, Record
from tint.matching import get_pairs
from tint.objects import init_current_objects, update_current_objects, \
    check_isolation
from tint.phase_correlation import get_global_shift


class CellTracks(object):
    """Cell track class

    This is the main class in the module. It allows tracks objects to be built
    using lists of PyArtGrid objects.

    This class comes from the TINT package with some modifications for our
    purposes.

    The following methods are available to the CellTracks classes:

        - :meth:`__save`:
            Saves deep copies of record, counter and current objects
        - :meth:`__load`:
            Loads saved copies of record, counter and current objects
        - :meth:`get_tracks`:
            Tracks the cells.
        - :meth:`get_object_prop`:
            Gets properties of an object.

    Attributes:
        field (str): Name of the field that is tracked. Defaults to
            reflectivity.
        params (dict): Parameter dictionary.
        last_grid (PyArtGrid): Last PyArtGrid object.
        counter (tint.helpers.counter): TINT Counter object.
        record (TrackRecord): TINT Record object.
        current_objects (dict): Ids and data of current objects.
        tracks (pandas.core.frame.DataFrame): DataFrame of cell tracks.
        __saved_record (TrackRecord): Deep copy of TINT Record object.
        __saved_counter (tint.helpers.Counter): Deep copy of TINT Counter
            object.
        __saved_objects (dict): Deep copy of current_objects.

    Args:
        field (str): Name of the field that is tracked. Defaults to
            reflectivity.
        params (dict): Parameter dictionary.

    """
    def __init__(self, params, field="reflectivity"):
        self.field = field
        self.params = params
        self.last_grid = None
        self.counter = None
        self.record = None
        self.current_objects = None
        self.tracks = pd.DataFrame()

        self.__saved_record = None
        self.__saved_counter = None
        self.__saved_objects = None

    def __save(self):
        """Saves deep copies of record, counter, and current_objects"""
        self.__saved_record = copy.deepcopy(self.record)
        self.__saved_counter = copy.deepcopy(self.counter)
        self.__saved_objects = copy.deepcopy(self.current_objects)

    def __load(self):
        """Loads saved copies of record, counter, and current_objects.

        If new tracks are appended to existing tracks via the get_tracks
        method, the most recent scan prior to the addition must be overwritten
        to link up with the new scans. Because of this, record, counter and
        current_objects must be reverted to their state in the penultimate
        iteration of the loop in get_tracks. See get_tracks for details.

        """
        self.record = self.__saved_record
        self.counter = self.__saved_counter
        self.current_objects = self.__saved_objects

    def get_tracks(self, grids):
        """Get tracks

        Obtains tracks given a list of pyart grid objects. This is the
        primary method of the CellTracks class.

        Args:
            grids (list_iterator): Iterator object of all grids.

        """
        # Tracks object being initialized
        grid_obj2 = next(grids)
        self.counter = Counter()
        self.record = TrackRecord(grid_obj2)

        raw2, frame2 = grid_obj2.extract_grid_data(self.field,
                                                   grid_obj2.grid_size,
                                                   self.params)
        new_rain = True

        while grid_obj2 is not None:
            grid_obj1 = grid_obj2
            raw1 = raw2
            frame1 = frame2

            try:
                grid_obj2 = next(grids)
            except StopIteration:
                grid_obj2 = None

            if grid_obj2 is not None:
                self.record.update_scan_and_time(grid_obj1, grid_obj2)
                raw2, frame2 = grid_obj2.extract_grid_data(self.field,
                                                           grid_obj2.grid_size,
                                                           self.params)
            else:
                # Setup to write final scan
                self.__save()
                self.last_grid = grid_obj1
                self.record.update_scan_and_time(grid_obj1)
                raw2 = None
                frame2 = np.zeros_like(frame1)

            if np.max(frame1) == 0:
                new_rain = True
                print("No cells found in scan", self.record.scan)
                self.current_objects = None
                continue

            global_shift = get_global_shift(raw1, raw2, self.params)
            pairs = get_pairs(frame1, frame2, global_shift,
                              self.current_objects, self.record, self.params)

            if new_rain:
                # First nonempty scan after a period of empty scans
                self.current_objects, self.counter = init_current_objects(
                    frame1, frame2, pairs, self.counter
                    )
                new_rain = False
            else:
                self.current_objects, self.counter = update_current_objects(
                    frame1, frame2, pairs, self.current_objects, self.counter
                    )

            obj_props = self.get_object_prop(frame1, grid_obj1)
            self.record.add_uids(self.current_objects)
            self.tracks = self.write_tracks(self.tracks, self.record,
                                            self.current_objects, obj_props)
            del grid_obj1, raw1, frame1, global_shift, pairs, obj_props
            # Scan loop end
        self.__load()

    def get_object_prop(self, image1, grid1):
        """Get object properties

        Returns dictionary of object properties for all objects found in
        image1.

        Args:
            image1 (numpy.ndarray): Image frame.
            grid1 (PyArtGrid): Current PyArtGrid.

        Returns:
            dict:
                Dictionary containing object properties.

        """
        id1 = []
        center = []
        grid_x = []
        grid_y = []
        area = []
        longitude = []
        latitude = []
        field_max = []
        max_height = []
        volume = []
        mask = []
        nobj = np.max(image1)

        unit_dim = self.record.grid_size
        unit_alt = unit_dim[0]/1000
        unit_area = (unit_dim[1]*unit_dim[2])/(1000**2)
        unit_vol = (unit_dim[0]*unit_dim[1]*unit_dim[2])/(1000**3)

        raw_3d = grid1.fields[self.field]['data'].data

        for obj in np.arange(nobj) + 1:
            obj_index = np.argwhere(image1 == obj)
            ind_mask = np.where(image1 == obj, image1, 0)
            mask.append(ind_mask)
            id1.append(obj)

            # 2D frame stats
            center.append(np.median(obj_index, axis=0))
            this_centroid = np.round(np.mean(obj_index, axis=0), 3)
            grid_x.append(this_centroid[1])
            grid_y.append(this_centroid[0])
            area.append(obj_index.shape[0] * unit_area)

            rounded = np.round(this_centroid).astype("i")
            lon = grid1.lon[rounded[0], rounded[1]]
            lat = grid1.lat[rounded[0], rounded[1]]
            longitude.append(lon)
            latitude.append(lat)

            # raw 3D grid stats
            obj_slices = [raw_3d[:, ind[0], ind[1]] for ind in obj_index]
            field_max.append(np.max(obj_slices))
            filtered_slices = [obj_slice > self.params['FIELD_THRESH']
                               for obj_slice in obj_slices]
            heights = [np.arange(raw_3d.shape[0])[ind]
                       for ind in filtered_slices]
            max_height.append(np.max(np.concatenate(heights)) * unit_alt)
            volume.append(np.sum(filtered_slices) * unit_vol)

        # cell isolation
        isolation = check_isolation(raw_3d, image1, self.record.grid_size,
                                    self.params)

        objprop = {'id1': id1,
                   'center': center,
                   'grid_x': grid_x,
                   'grid_y': grid_y,
                   'area': area,
                   'field_max': field_max,
                   'max_height': max_height,
                   'volume': volume,
                   'lon': longitude,
                   'lat': latitude,
                   'isolated': isolation,
                   'mask': mask}
        return objprop

    @staticmethod
    def write_tracks(old_tracks, record, current_objects, obj_props):
        """Writes all cell information to tracks dataframe

        This is basically the exact TINT method, I just added the property
        'mask' to know exactly where the cell is located, not only the cell
        center.

        Args:
            old_tracks (pandas.core.frame.DataFrame): DataFrame containing
                the previous tracks.
            record (TrackRecord): Object containing the TINT TrackRecord.
            current_objects (dict): Dictionary containing the currently
                tracked objects.
            obj_props (dict): Dictionary containing the currently tracked
                object properties.

        Returns:
             pandas.core.frame.DataFrame:
                DataFrame where the new tracks have been appended.

        """
        print("Writing tracks for scan", record.scan)

        nobj = len(obj_props['id1'])
        scan_num = [record.scan] * nobj
        uid = current_objects['uid']

        new_tracks = pd.DataFrame({
            'scan': scan_num,
            'uid': uid,
            'time': record.time,
            'grid_x': obj_props['grid_x'],
            'grid_y': obj_props['grid_y'],
            'lon': obj_props['lon'],
            'lat': obj_props['lat'],
            'area': obj_props['area'],
            'vol': obj_props['volume'],
            'max': obj_props['field_max'],
            'max_alt': obj_props['max_height'],
            'isolated': obj_props['isolated'],
            'mask': obj_props['mask']
            })
        new_tracks.set_index(["scan", "uid"], inplace=True)
        tracks = old_tracks.append(new_tracks)
        return tracks


class TrackRecord(Record):
    """Record object of cell tracks

    This class inherits from the TINT Record class. It only overwrites the
    'update_scan_and_time' method for better handling of the grid time
    extraction. For all other documentation, see tint.helpers.Record
    documentation.

    """
    def update_scan_and_time(self, grid_obj1, grid_obj2=None):
        """Update scan number and time

        Updates the scan number and associated time. This information is
        used for obtaining object properties as well as for the interval ratio
        correction of last_heads vectors.

        Args:
            grid_obj1 (PyArtGrid): First grid.
            grid_obj2 (PyArtGrid): Second grid.

        """
        self.scan += 1
        self.time = grid_obj1.parse_grid_datetime()
        if grid_obj2 is None:
            # tracks for last scan are being written
            return
        time2 = grid_obj2.parse_grid_datetime()
        old_diff = self.interval
        self.interval = time2 - self.time
        if old_diff is not None:
            self.interval_ratio = self.interval.seconds/old_diff.seconds
