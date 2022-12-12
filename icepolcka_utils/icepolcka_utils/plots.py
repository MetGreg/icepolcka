"""Plotting module

Contains all functions/classes related to plotting.

"""
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt
import matplotlib.pyplot as plt
import matplotlib.ticker as mplticker


class PlotConfig:
    """Save plot settings

    This class serves as a container for plot settings. Given a number of parameters, this class
    saves these configuration as attributes.

    The instance of this class with the saved parameters can then be passed to plotting routines
    to access the plotting configuration parameters.

    Args:
        image_cfg (dict): Optional image configurations.
        grid_cfg (dict): Optional grid configurations.
        fonts_cfg (dict): Optional fonts configurations.

    Attributes:
        image (dict): Image configurations.
        grid (dict): Image configurations.
        fonts (dict): Fonts configurations.

    """
    def __init__(self, image_cfg=None, grid_cfg=None, fonts_cfg=None):
        self.fonts = {}
        self.image = {}
        self.grid = {}
        self._set_default()
        if image_cfg is not None:
            for key, value in image_cfg.items():
                self.image[key] = value
        if grid_cfg is not None:
            for key, value in grid_cfg.items():
                self.grid[key] = value
        if fonts_cfg is not None:
            for key, value in fonts_cfg.items():
                self.fonts[key] = value

    def _set_default(self):
        self.image = {
            'vmin': None,
            'vmax': None,
            'cmap': None,
            'alpha': 1,
            'xlabel': None,
            'ylabel': None,
            'title': None,
            'extent': [10.53, 12.65, 47.43, 48.85],
            'cities': ["Munich", "Augsburg"]
            }
        self.grid = {
            'x_axis': True,
            'y_axis': True,
            'width': 2,
            }
        self.fonts = {
            'small_city': 12,
            'big_city': 15,
            'xticks': 16,
            'yticks': 16,
            'xlabel': 18,
            'ylabel': 18,
            'title': 20,
            }


def plot_munich(data, grid, cfg, axis=None, levels=None):
    """Plot data on a Munich map

    Args:
        data (~numpy.ndarray): Data to be plotted. Must be 2D array.
        grid (~xarray.Dataset): Containing the grid lon/lat coordinates. These coordinates must be
            of same shape as data.
        cfg (PlotConfig): Dictionary containing plot configurations.
        axis (~matplotlib.axes.Axes): Matplotlib axis to which the image is plotted.
        levels (~numpy.ndarray): Numpy array to set the colorbar levels.

    Returns:
        (~matplotlib.collections.QuadMesh or cartopy.mpl.contour.GeoContourSet):
            Matplotlib image with data on a Munich background map.

    """
    if axis is None:
        _, axis = _create_figure()
    axis = _plot_background(axis, cfg.image['extent'])
    data = np.where(data >= cfg.image['vmin'], data, np.nan)  # Filter values below min threshold

    # Transform coordinates to map projection and create figure
    coordinates = axis.projection.transform_points(ccrs.Geodetic(), grid.lon.values,
                                                   grid.lat.values)
    if levels is not None:
        img = axis.contourf(coordinates[:, :, 0], coordinates[:, :, 1], data, levels,
                            alpha=cfg.image['alpha'], vmin=cfg.image['vmin'],
                            vmax=cfg.image['vmax'], cmap=cfg.image['cmap'], extend="max")
    else:
        img = axis.pcolormesh(coordinates[:, :, 0], coordinates[:, :, 1], data,
                              alpha=cfg.image['alpha'], vmin=cfg.image['vmin'],
                              vmax=cfg.image['vmax'], cmap=cfg.image['cmap'])
    axis = _add_features(axis)
    axis = _add_cities(axis, cfg.image['cities'], cfg.fonts)
    _add_grid(axis, cfg)
    axis.set_title(cfg.image['title'], fontdict={'fontsize': cfg.fonts['title']})
    return img


def create_subplots():
    """Create subplots

    Creates the figure and axis for a panel plot. One main figure and axis is created that will be
    used for labeling, and 6 smaller subplots are created that will be reserved for the actual
    plots.

    Returns:
        (~matplotlib.figure.Figure, ~numpy.ndarray):
            1) Matplotlib figure.
            2) Array of all axes.

    """
    fig = plt.figure(figsize=(8, 5))
    request = cimgt.Stamen("terrain-background")
    axis = fig.add_subplot(111)
    axis.spines['top'].set_color('none')
    axis.spines['bottom'].set_color('none')
    axis.spines['left'].set_color('none')
    axis.spines['right'].set_color('none')
    axis.tick_params(labelcolor="w", top=False, bottom=False, left=False, right=False)
    grid_spec = fig.add_gridspec(2, 3, hspace=0.1, wspace=0.1)
    axes = grid_spec.subplots(sharex="col", sharey="row", subplot_kw={'projection': request.crs})
    return fig, axes


def _add_cities(axis, cities, fonts):
    """Add city names

    Adds some city names to the map. For each of the given city names, this function adds a text
    box.

    Args:
        axis (cartopy.mpl.geoaxes.GeoAxesSubplot): Axis to which the city names will be added.
        cities (list): List of city names to plot.
        fonts(dict): Font sizes for small and big cities.

    Returns:
        ax:
            cartopy.mpl.geoaxes.GeoAxesSubplot:
                Axis where the city names have been added.

    """
    cities_larger = {'Munich': (11.583333, 48.18), 'Nuremberg': (11.068333, 49.447778)}
    cities_smaller = {'Augsburg': (10.898514, 48.371538), 'Regensburg': (12.119234, 49.034512)}

    for city in cities:
        if city in cities_larger:
            x_loc, y_loc = cities_larger[city][0], cities_larger[city][1]
            plt.annotate(city, xy=(x_loc, y_loc + 0.025), ha="center", fontsize=fonts['big_city'],
                         xycoords=ccrs.Geodetic()._as_mpl_transform(axis))
        elif city in cities_smaller:
            x_loc, y_loc = cities_smaller[city][0], cities_smaller[city][1]
            plt.annotate(city, xy=(x_loc, y_loc + 0.025), ha="center", fontsize=fonts['small_city'],
                         xycoords=ccrs.Geodetic()._as_mpl_transform(axis))
    return axis


def _add_features(axis):
    """Add features to image

    Adds some features to the map. This includes rivers, roads and lakes.

    Args:
        axis (cartopy.mpl.geoaxes.GeoAxesSubplot): Axes to which the features will be added.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Axis, where the features have been added.

    """
    roads = cfeature.NaturalEarthFeature("cultural", "roads", "10m")
    rivers_10m = cfeature.NaturalEarthFeature("physical", "rivers_lake_centerlines", "10m")
    rivers_eu = cfeature.NaturalEarthFeature("physical", "rivers_europe", "10m")
    lakes_eu = cfeature.NaturalEarthFeature("physical", "lakes_europe", "10m")
    lakes_10m = cfeature.NaturalEarthFeature("physical", "lakes", "10m")
    axis.add_feature(rivers_10m, edgecolor="deepskyblue", facecolor="None", linewidth=0.3)
    axis.add_feature(rivers_eu, edgecolor="deepskyblue", facecolor="None", linewidth=0.2)
    axis.add_feature(lakes_10m, edgecolor="deepskyblue", facecolor="None", linewidth=0.5)
    axis.add_feature(lakes_eu, edgecolor="deepskyblue", facecolor="None", linewidth=0.5)
    axis.add_feature(lakes_10m, edgecolor="None", facecolor="deepskyblue", linewidth=0.5, alpha=0.3)
    axis.add_feature(lakes_eu, edgecolor="None", facecolor="deepskyblue", linewidth=0.5, alpha=0.3)
    axis.add_feature(roads, edgecolor="grey", facecolor="None", linewidth=0.3)
    axis.add_feature(cfeature.BORDERS.with_scale("10m"))
    return axis


def _add_grid(axis, cfg):
    """Add grid

    Adds grid lines and axis labels.

    Args:
        axis (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis onto which the grid will be
            drawn.
        cfg (PlotConfig): Plotting configuration.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis onto which the grid has been added.

    """
    # Grid lines
    g_lines = axis.gridlines(alpha=1, color="grey", linestyle="--", linewidth=cfg.grid['width'],
                             draw_labels=True)
    loc = mplticker.MaxNLocator(nbins=4)
    g_lines.xlocator = loc
    g_lines.ylocator = loc
    g_lines.xlabel_style = {'size': cfg.fonts['xticks']}
    g_lines.ylabel_style = {'size': cfg.fonts['yticks']}
    g_lines.top_labels = False
    g_lines.right_labels = False
    if not cfg.grid['x_axis']:
        g_lines.bottom_labels = False
    if not cfg.grid['y_axis']:
        g_lines.left_labels = False
    if cfg.image['xlabel']:
        axis.text(-0.08, 0.55, "Latitude (°N)", va="bottom", ha="center", rotation="vertical",
                  rotation_mode="anchor", transform=axis.transAxes, fontsize=cfg.fonts['xlabel'])
    if cfg.image['ylabel']:
        axis.text(0.5, -0.08, "Longitude (°E)", va="bottom", ha="center", rotation="horizontal",
                  rotation_mode="anchor", transform=axis.transAxes, fontsize=cfg.fonts['ylabel'])
    return axis


def _plot_background(axis, extent, zoom=7):
    """Plot the image background

    The background map tiles are taken from Stamen Design (http://stamen.com).
    Their data comes from OpenStreetMap (http://openstreetmap.org).

    Args:
        axis (cartopy.mpl.geoaxes.GeoAxesSubplot): Axis to which the background will be added.
        extent (list): Extent of map (lon_min, lon_max, lat_min, lat_max).
        zoom (int): Zoom level of background image.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis that includes the background image.

    """
    request = cimgt.Stamen("terrain-background")
    axis.set_extent(extent)
    axis.add_image(request, zoom, alpha=0.5, interpolation="spline36")
    return axis


def _create_figure():
    """Create a matplotlib figure

    Returns:
        (matplotlib.figure.Figure, cartopy.mpl.geoaxes.GeoAxesSubplot):
            1) Matplotlib Figure.
            2) Matplotlib axis.

    """
    request = cimgt.Stamen("terrain-background")
    fig = plt.figure(figsize=(10, 10))
    axis = plt.axes(projection=request.crs)
    return fig, axis
