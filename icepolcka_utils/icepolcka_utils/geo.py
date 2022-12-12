"""Geographic calculations for distances, heights or compass bearings

This module contains all functions that are related to any kind of distance-, height- or bearing-
calculations.

"""
import math
import numpy as np


def get_bin_altitude(r_coord, theta, site_alt=0, r_e=6371000, k=4/3):
    """Calculates the height of a radar bin taking the refractivity of the atmosphere into account.

    Function taken from wradlib.org

    Based on `Doviak et al.` the bin altitude is calculated as

    .. math::

        h = \\sqrt{r^2 + (k a)^2 + 2 r k a \\sin\\theta} - k a

    Args:
        r_coord (numpy.ndarray or float): Array of ranges [m].
        theta (numpy.ndarray or float): Elevation angles in degrees with 0° at horizontal and +90°
            pointing vertically upwards from the radar. Broadcastable to the shape of r.
        site_alt (float): Altitude in [m] above mean sea level of the referencing radar site.
        r_e (float): Earth's radius [m].
        k (float): Adjustment factor to account for the refractivity gradient that affects radar
            beam propagation. In principle this is wavelength-dependent. The default of 4/3 is a
            good approximation for most weather radar wavelengths.

    Returns:
        numpy.ndarray or float:
            Array of heights of the radar bins in [m].

    """
    height = (np.sqrt(r_coord**2 + (k*r_e)**2 + 2*r_coord*k*r_e*np.sin(np.radians(theta))) - k*r_e
              + site_alt)
    return height


def get_bin_distance(r_coord, theta, site_alt=0, r_e=6371000, k=4/3):
    """Calculates the distance between range bin and site

    Calculates the great circle distance while taking the refractivity of the atmosphere into
    account. Function taken from wradlib.org

    Based on `Doviak et al.` the site distance may be calculated as

    .. math::

        s = k a \\arcsin\\left(\\frac{r \\cos\\theta}{k a + h(r, \\theta, a, k)}\\right)

    where :math:`h` would be provided by :func:`get_bin_altitude`

    Args:
        r_coord (numpy.ndarray or float): Array of ranges [m].
        theta (numpy.ndarray or float): Elevation angles in degrees with 0° at horizontal and +90°
            pointing vertically upwards from the radar. Broadcastable to the shape of r.
        site_alt (float): Site altitude [m] above mean sea level. Same shape as r.
        r_e (float): Earth's radius [m].
        k (float): Adjustment factor to account for the refractivity gradient that affects radar
            beam propagation. In principle this is wavelength-dependent. The default of 4/3 is a
            good approximation for most weather radar wavelengths.

    Returns:
        numpy.ndarray or float:
            Array of great circle arc distances [m].

    """
    height = get_bin_altitude(r_coord, theta, site_alt, r_e, k)
    s_arc = k*r_e*np.arcsin((r_coord*np.cos(np.radians(theta)))/(k*r_e + height))
    return s_arc


def get_pos_from_dist(site_location, distance, azimuth, r_e=6371000):
    """Get coordinates from distance and bearing

    Given a site location, a distance along the surface and a compass bearing to a target, this
    method returns the geographical coordinates of this target.

    Args:
        site_location (tuple): (Longitude, Latitude) coordinates of site.
        distance (float): Distance to target [m].
        azimuth (float): Azimuth angle from site towards target.
        r_e (float): Earth radius [m].

    Returns:
        (float, float):
            1) Longitude of target in decimal degrees.
            2) Latitude of target in decimal degrees.

    """
    bearing = math.radians(azimuth)
    lon1 = math.radians(site_location[0])
    lat1 = math.radians(site_location[1])
    lat2 = math.asin(math.sin(lat1)*math.cos(distance/r_e) +
                     math.cos(lat1)*math.sin(distance/r_e)*math.cos(bearing))
    lon2 = lon1 + math.atan2(math.sin(bearing)*math.sin(distance/r_e)*math.cos(lat1),
                             math.cos(distance/r_e)-math.sin(lat1)*math.sin(lat2))
    return math.degrees(lon2), math.degrees(lat2)


def get_target_distance(radar, target, r_e=6371000):
    """Calculates the distance of a target from the radar.

    Args:
        radar (tuple or list): Longitude, Latitude of the radar. Must be given in decimal degrees.
        target (tuple or list): Longitude, Latitude of the target. Must be given in decimal degrees.
        r_e (float): Earth's radius [m].

    Returns:
        float:
            The distance in meters.

    """
    lon_radar = math.radians(radar[0])
    lat_radar = math.radians(radar[1])
    lon_target = math.radians(target[0])
    lat_target = math.radians(target[1])

    d_lat = lat_target-lat_radar
    d_lon = lon_target-lon_radar

    a_var = math.sin(d_lat/2) * math.sin(d_lat/2) \
        + math.sin(d_lon/2) * math.sin(d_lon/2) * math.cos(lat_radar) * math.cos(lat_target)
    c_fac = 2 * math.atan2(math.sqrt(a_var), math.sqrt(1-a_var))
    return r_e * c_fac
