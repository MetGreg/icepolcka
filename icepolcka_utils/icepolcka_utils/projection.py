"""Projections and Coordinate Transformations

This module contains all functions that are related to projections, coordinate systems and
coordinate transformations.

"""
import numpy as np
import wradlib as wrl
from osgeo import osr

from icepolcka_utils.geo import get_bin_distance, get_bin_altitude


def spherical_to_cart(r_coord, azi, elv, site_coords):
    """Transform spherical radar coordinates to Cartesian xyz

    The basic structure of this function is taken from wradlib.org

    From the radius and elevation coordinates, the distance to the radar and the height of each bin
    above ground is calculated. From the calculated distance and the azimuth angle, the Cartesian x,
    y - coordinates with the radar site at (0, 0) are calculated using the Azimuthal_Equidistant
    projection.

    The r, az, and elv - arrays must be of exactly the same shape, so that each value corresponds to
    exactly one measurement bin.

    The site_coords is a tuple of lon/lat/alt, or lon/lat, if the site altitude is zero.

    Args:
        r_coord (~numpy.ndarray): Numpy array of ranges [m].
        azi (~numpy.ndarray): Numpy array of azimuth angles. Must be of same shape as r.
        elv (~numpy.ndarray): Numpy array of elevation angles. Must be of same shape as r and az.
        site_coords (tuple): Radar site coordinates as a tuple of (lon, lat, alt). If the length of
            the tuple is two, the altitude is assumed to be zero.

    Raises:
        TypeError: If the input coordinates are no numpy.ndarray.
        AssertionError: If the input coordinates don't have the same shape.
        ValueError: If site coordinates are not a tuple with length 3 or 2.

    Returns:
            (~numpy.ndarray, osgeo.osr.SpatialReference):
                1) The array of Cartesian coordinates of all bins [m]. This is equal to a shape of
                   (r_coord.shape, 3).
                2) The projection that corresponds to the coordinate array.

    """
    if not all(isinstance(i, np.ndarray) for i in [r_coord, azi, elv]):
        raise TypeError("Range, azimuth and elevation must be numpy arrays")
    if r_coord.shape != azi.shape or r_coord.shape != elv.shape:
        raise AssertionError("Range, azimuth and elevation must have same shape!")
    if len(site_coords) == 2:
        site_alt = 0
    elif len(site_coords) == 3:
        site_alt = site_coords[2]
    else:
        raise ValueError("Site coordinates not in correct shape")

    dist = get_bin_distance(r_coord, elv, site_alt)

    proj = _proj4_to_osr(
        ("+proj=aeqd +lon_0={lon:f} +x_0=0 +y_0=0 " + "+lat_0={lat:f} +ellps=WGS84 +datum=WGS84 " +
         "+units=m +no_defs").format(lon=site_coords[0], lat=site_coords[1])
        )
    x_grid = dist*np.cos(np.radians(90 - azi))
    y_grid = dist*np.sin(np.radians(90 - azi))
    z_grid = get_bin_altitude(r_coord, elv, site_alt)
    xyz = np.concatenate((x_grid[..., np.newaxis], y_grid[..., np.newaxis],
                          z_grid[..., np.newaxis]), axis=-1)
    return xyz, proj


def geo_to_cart(geo, origin):
    """Transform geographical to Cartesian coordinates

    Args:
        geo (~numpy.ndarray): Array of geographical coordinates (lon, lat).
        origin (tuple or list): (lon, lat) of origin.

    Returns:
        (numpy.ndarray, osgeo.osr.SpatialReference):
            1) Array of the corresponding Cartesian coordinates.
            2) The projection that corresponds to the Cartesian coordinates.

    """
    proj_geo = osr.SpatialReference()
    proj_geo.ImportFromEPSG(4326)
    proj_cart = _proj4_to_osr(
        ("+proj=aeqd +lon_0={lon:f} +x_0=0 +y_0=0 " + "+lat_0={lat:f} +ellps=WGS84 +datum=WGS84 " +
         "+units=m +no_defs").format(lon=origin[0], lat=origin[1]))
    cart = wrl.georef.reproject(geo, projection_source=proj_geo, projection_target=proj_cart)
    return cart, proj_cart


def data_to_cart(data, src, trg, itp=None, method="Idw"):
    """Interpolate data to a Cartesian target grid

    Interpolates data to a Cartesian grid using Inverse Distance from wradlib.org.

    Args:
        data (~numpy.ndarray): 1D array of data.
        src (~numpy.ndarray): Corresponding source coordinates. For each data entry, the
            corresponding Cartesian (x,y,z)-coordinates. Shape of (len(data), 3).
        trg (~numpy.ndarray): Coordinates of target grid. Shape of ('a', 3). This equals a grid of
            'a' grid points, for each the Cartesian (x,y,z)-coordinates must be given.
        itp (wradlib interpolator, e.g., :obj:`~wradlib.ipol.Nearest`): Mapping from source  to
            target grid. If None, it will be calculated.
        method (str): Interpolation method to be used. This uses the corresponding Wradlib
            interpolation. I suggest to use either 'Idw' (inverse distance) or 'Nearest' (nearest
            neighbor).

    Returns:
        (numpy.ndarray, wradlib interpolator (e.g., :obj:`~wradlib.ipol.Nearest`)):
            1) Interpolated data array.
            2) Mapping function that was used for the interpolation.

    """
    if itp is None:
        itp = getattr(wrl.ipol, method)(src, trg)
    data_int = itp(data)
    return data_int, itp


def _proj4_to_osr(proj4str):
    proj = osr.SpatialReference()
    proj.ImportFromProj4(proj4str)
    proj.AutoIdentifyEPSG()
    return proj
