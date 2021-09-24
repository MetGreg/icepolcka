"""Projections and Coordinate Transformations

This module contains all functions that are related to projections,
coordinate systems and coordinate transformations.

"""
import numpy as np
import wradlib as wrl
from osgeo import osr, ogr

from icepolcka_utils.geo import get_bin_distance, get_bin_altitude


def spherical_to_cart(r, az, elv, site_coords):
    """Transform spherical radar coordinates to Cartesian xyz

    The basic structure of this function is taken from wradlib.org

    From the radius and elevation coordinates, the distance to the radar and
    the height of each bin above ground is calculated. From the
    calculated distance and the azimuth angle, the Cartesian x,
    y - coordinates with the radar site at (0, 0) are calculated using the
    Azimuthal_Equidistant projection.

    The r, az, and elv - arrays must be of exactly the same shape, so that
    each value corresponds to exactly one measurement bin.

    The site_coords is a tuple of lon/lat/alt, or lon/lat, if the site
    altitude is zero.

    Args:
        r (numpy.ndarray): Numpy array of ranges [m].
        az (numpy.ndarray): Numpy array of azimuth angles. Must be of same
            shape as r.
        elv (numpy.ndarray): Numpy array of elevation angles. Must be of same
            shape as r and az.
        site_coords (tuple): Radar site coordinates as a tuple of (lon, lat,
            alt). If the length of the tuple is two, the altitude is assumed to
            be zero.

    Raises:
        TypeError: If the input coordinates are no numpy.ndarray.
        AssertionError: If the input coordinates don't have the same shape.
        ValueError: If site coordinates are not a tuple with length 3 or 2.

    Returns:
            (numpy.ndarray, SpatialReference):
                1) The two dimensional array of Cartesian coordinates of all
                    bins [m]. This is equal to a shape of (r.shape, 3).
                2) The projection that corresponds to the coordinate array.

    """
    if type(r) != np.ndarray or type(az) != np.ndarray or type(elv) != \
            np.ndarray:
        raise TypeError("Range, azimuth and elevation must be numpy arrays")
    if r.shape != az.shape or r.shape != elv.shape:
        raise AssertionError("Range, azimuth and elevation must have same "
                             "shape!")
    if len(site_coords) == 2:
        site_alt = 0
    elif len(site_coords) == 3:
        site_alt = site_coords[2]
    else:
        raise ValueError("Site coordinates not in correct shape")

    dist = get_bin_distance(r, elv, site_alt)

    proj = proj4_to_osr(("+proj=aeqd +lon_0={lon:f} +x_0=0 +y_0=0 " +
                         "+lat_0={lat:f} +ellps=WGS84 +datum=WGS84 " +
                         "+units=m +no_defs").format(lon=site_coords[0],
                                                     lat=site_coords[1]))
    x = dist*np.cos(np.radians(90 - az))
    y = dist*np.sin(np.radians(90 - az))
    z = get_bin_altitude(r, elv, site_alt)
    xyz = np.concatenate((x[..., np.newaxis], y[..., np.newaxis],
                          z[..., np.newaxis]), axis=-1)
    return xyz, proj


def proj4_to_osr(proj4str):
    """Transform a proj4 string to an osr SpatialReference object

    Creates an osr.SpatialReference object from the given proj4-string.

    Code from wradlib.org.

    Args:
        proj4str (str): Proj4 string describing the projection.

    Raises:
        ValueError: If proj4str is not valid.

    Returns:
        SpatialReference:
            The SpatialReference that corresponds to the given proj4str.

    """
    proj = osr.SpatialReference()
    proj.ImportFromProj4(proj4str)
    proj.AutoIdentifyEPSG()
    if proj.Validate() == ogr.OGRERR_CORRUPT_DATA:
        raise ValueError("proj4str validates to 'ogr.OGRERR_CORRUPT_DATA'"
                         "and can't be imported as OSR object")
    return proj


def geo_to_cart(geo, origin):
    """Transform geographical to Cartesian coordinates

    Args:
        geo (numpy.ndarray): Array of geographical coordinates (lon, lat).
        origin (tuple or list): (lon, lat) of origin.

    Returns:
        (numpy.ndarray, SpatialReference):
            1) Array of the corresponding Cartesian coordinates.
            2) The projection that corresponds to the Cartesian coordinates.

    """
    proj_geo = osr.SpatialReference()
    proj_geo.ImportFromEPSG(4326)
    proj_cart = proj4_to_osr(("+proj=aeqd +lon_0={lon:f} +x_0=0 +y_0=0 "
                              + "+lat_0={lat:f} +ellps=WGS84 +datum=WGS84 "
                              + "+units=m +no_defs").format(lon=origin[0],
                                                            lat=origin[1]))
    cart = wrl.georef.reproject(geo, projection_source=proj_geo,
                                projection_target=proj_cart)
    return cart, proj_cart


def data_to_cart(data, src, trg, itp=None, maxdist=3000):
    """Interpolate data to a Cartesian target grid

    Interpolates data to a Cartesian grid using Inverse Distance from
    wradlib.org.

    Args:
        data (numpy.ndarray): 1D array of data.
        src (numpy.ndarray): Corresponding source coordinates. For each data
            entry, the corresponding Cartesian (x,y,z)-coordinates. Shape of
            (len(data), 3).
        trg (numpy.ndarray): Coordinates of target grid. Shape of (a, 3). This
            equals a grid of 'a' grid points, for each the
            Cartesian (x,y,z)-coordinates must be given.
        itp (wradlib interpolator): Mapping from source to target grid. If
            None, it will be calculated.
        maxdist (float): Maximum distance [m] between source and target
            coordinate point that is interpolated.

    Returns:
        (numpy.ndarray, wradlib.ipol-object):
            1) Interpolated data array.
            2) Mapping function that was used for the interpolation.

    """
    if itp is None:
        itp = wrl.ipol.Nearest(src, trg)
    data_int = itp(data, maxdist=maxdist)
    return data_int, itp
