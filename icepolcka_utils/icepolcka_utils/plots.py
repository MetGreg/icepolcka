"""Plotting module

Contains all functions/classes related to plotting.

"""
import datetime as dt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mplticker
import numpy as np
import cartopy.feature as cfeature


def create_figure():
    """Create a matplotlib figure

    Returns:
        (matplotlib.figure.Figure, cartopy.mpl.geoaxes.GeoAxesSubplot):
            1) Matplotlib Figure.
            2) Matplotlib axis.

    """
    request = cimgt.Stamen("terrain-background")
    fig = plt.figure(figsize=(10, 10))
    ax = plt.axes(projection=request.crs)
    return fig, ax


def add_cities(ax, cities):
    """Add city names

    Adds some city names to the map. For each of the given city names,
    this function adds a text box.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Axis to which the city names
            will be added.
        cities (list): List of city names to plot.

    Returns:
        ax:
            cartopy.mpl.geoaxes.GeoAxesSubplot:
                Axis where the city names have been added.

    """
    cities_larger = {'München': (11.583333, 48.18),
                     'Nürnberg': (11.068333, 49.447778)}
    cities_smaller = {
        'Augsburg': (10.898514, 48.371538),
        'Regensburg': (12.119234, 49.034512)
        }

    for city in cities:
        if city in cities_larger.keys():
            x, y = cities_larger[city][0], cities_larger[city][1]
            plt.annotate(city, xy=(x, y + 0.025), ha="center", fontsize=15,
                         xycoords=ccrs.Geodetic()._as_mpl_transform(ax))
        elif city in cities_smaller.keys():
            x, y = cities_smaller[city][0], cities_smaller[city][1]
            plt.annotate(city, xy=(x, y + 0.025), ha="center", fontsize=12,
                         xycoords=ccrs.Geodetic()._as_mpl_transform(ax))
    return ax


def add_features(ax):
    """Add features to image

    Adds some features to the map. This includes rivers, roads and lakes.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Axes to which the features
            will be added.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Axis, where the features have been added.

    """
    roads = cfeature.NaturalEarthFeature("cultural", "roads", "10m")
    rivers_10m = cfeature.NaturalEarthFeature("physical",
                                              "rivers_lake_centerlines", "10m")
    rivers_eu = cfeature.NaturalEarthFeature("physical", "rivers_europe", "10m")
    lakes_eu = cfeature.NaturalEarthFeature("physical", "lakes_europe", "10m")
    lakes_10m = cfeature.NaturalEarthFeature("physical", "lakes", "10m")
    ax.add_feature(rivers_10m, edgecolor="deepskyblue", facecolor="None",
                   linewidth=0.3)
    ax.add_feature(rivers_eu, edgecolor="deepskyblue", facecolor="None",
                   linewidth=0.2)
    ax.add_feature(lakes_10m, edgecolor="deepskyblue", facecolor="None",
                   linewidth=0.5)
    ax.add_feature(lakes_eu, edgecolor="deepskyblue", facecolor="None",
                   linewidth=0.5)
    ax.add_feature(lakes_10m, edgecolor="None", facecolor="deepskyblue",
                   linewidth=0.5, alpha=0.3)
    ax.add_feature(lakes_eu, edgecolor="None", facecolor="deepskyblue",
                   linewidth=0.5, alpha=0.3)
    ax.add_feature(roads, edgecolor="grey", facecolor="None", linewidth=0.3)
    ax.add_feature(cfeature.BORDERS.with_scale("10m"))
    return ax


def plot_background(ax, extent, zoom=7):
    """Plot the image background

    The background map tiles are taken from Stamen Design (http://stamen.com).
    Their data comes from OpenStreetMap (http://openstreetmap.org).

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Axis to which the background
            will be added.
        extent (list): Extent of map (lon_min, lon_max, lat_min, lat_max).
        zoom (int): Zoom level of background image.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis that includes the background image.

    """
    request = cimgt.Stamen("terrain-background")
    ax.set_extent(extent)
    ax.add_image(request, zoom, alpha=0.5, interpolation="spline36")
    return ax


def add_grid(ax):
    """Add grid

    Adds grid lines and axis labels.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis onto which
            the grid will be drawn.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis onto which the grid has been added.

    """
    # Grid lines
    gl = ax.gridlines(alpha=1, color="grey", linestyle="--", linewidth=2,
                      draw_labels=True)
    loc = mplticker.MaxNLocator(nbins=4)
    gl.xlocator = loc
    gl.ylocator = loc
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 16}
    gl.ylabel_style = {'size': 16}
    ax.text(-0.08, 0.55, "Latitude (°N)", va="bottom", ha="center",
            rotation="vertical", rotation_mode="anchor",
            transform=ax.transAxes, fontsize=20)
    ax.text(0.5, -0.08, "Longitude (°E)", va="bottom", ha="center",
            rotation="horizontal", rotation_mode="anchor",
            transform=ax.transAxes, fontsize=20)
    return ax


def plot_tracks(tobj, grids, extent, levels, cities, output, alt=None,
                cmap=None, persist=False, cell_text=False):
    """Plots tracks in an euler way

    This function is originally from TINT and adapted to my likings.

    Args:
        tobj (CellTracks): CellTracks object.
        grids (list): List of PyArtGrid objects.
        extent (list): Extent of map (lon_min, lon_max, lat_min, lat_max).
        levels (numpy.ndarray): Levels of contour plot.
        cities (list): List of city names to plot on background image.
        output (str): Name of output folder.
        alt (int): Height [m] to plot.
        cmap (matplotlib colormap):
        persist (bool): Whether to keep tracks of dead cells.
        cell_text (bool): Whether to draw cell IDs.

    """
    if alt is None:
        alt = tobj.params['GS_ALT']

    # Create tracer object
    tracer = Tracer(tobj, persist)

    # Get number of frames to plot
    nframes = len(grids)
    print("Animating", nframes, "frames")

    # Loop through all time steps and create plot for each
    for nframe, grid in enumerate(grids):
        time = dt.datetime.strftime(dt.datetime.utcfromtimestamp(
            grid.time['data'][0]), "%Y-%m-%d %H:%M:%S")
        print("Frame:", nframe)

        # Create figure, add extent and background image
        fig, ax = create_figure()
        ax = plot_background(ax, extent)

        # Transform coordinates to map projection and create figure
        coordinates = ax.projection.transform_points(ccrs.Geodetic(), grid.lon,
                                                     grid.lat)
        level = grid.get_grid_alt(alt)
        refl = grid.fields['reflectivity']['data'][level]
        img = ax.contourf(coordinates[:, :, 0], coordinates[:, :, 1], refl,
                          levels, alpha=0.7, vmin=0, vmax=60, extend="max",
                          cmap=cmap)
        ax = add_features(ax)
        ax = add_cities(ax, cities)

        # Add tracer and cell identifier
        if nframe in tobj.tracks.index.to_frame()['scan']:
            frame_tracks = tobj.tracks.loc[nframe]

            # Plot tracer
            tracer.update(nframe)
            tracer.plot(ax)

            # Add cell identifier text
            if cell_text:
                for ind, uid in enumerate(frame_tracks.index):
                    x = frame_tracks['lon'].iloc[ind]
                    y = frame_tracks['lat'].iloc[ind]
                    text_coords = ax.projection.transform_points(
                        ccrs.Geodetic(), np.array(x), np.array(y)
                        )[0]
                    ax.text(text_coords[0], text_coords[1], uid, fontsize=20)

        # Tick layout
        add_grid(ax)

        # Add colorbar
        cbar = plt.colorbar(img, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=20)
        cbar.set_label(label="dBZ", fontsize=20)

        # Add title
        plt.title(time + " [UTC]", fontsize=20, y=1.05)

        # Save figure
        plt.tight_layout()
        plt.savefig(output + str(nframe) + ".png", bbox_inches="tight")
        plt.close()


class Tracer(object):
    """Tracer class to visualize cell tracks

    This class originates from the TINT-package:
    https://github.com/openradar/TINT

    Some methods are modified, some are added for our purposes.

    The following methods are available:

         - :meth:`create_colors`:
            Creates the colors to use for cell tracers.
         - :meth:`update`:
            Updates the tracked cells.
         - :meth:`_check_uid`:
            Checks the tracer colors.
         - :meth:`plot`:
            Plots the cell tracers

    Attributes:
        colors (list): Colors to use for tracers.
        tobj (CellTracks): CellTracks object.
        persist (bool): Whether to keep dead cells.
        color_stack (list): Stacked color list.
        cell_color (pandas.core.series.Series): DataFrame of colors
            associated to the cells.
        history (pandas.core.frame.DataFrame): DataFrame of all past cells.
        current (pandas.core.frame.DataFrame): DataFrame of all current cells.

    Args:
        tobj (CellTracks): CellTracks object.
        persist (bool): Whether to keep dead cells.

    """
    def __init__(self, tobj, persist):
        self.colors = self.create_colors()
        self.tobj = tobj
        self.persist = persist
        self.color_stack = self.colors * 10
        self.cell_color = pd.Series()
        self.history = None
        self.current = None

    def create_colors(self):
        """Define colors to use for tracers

        Returns:
            list:
                Matplotlib color names to use for tracers.

        """
        colors_excluded = ["black", "dimgray", "dimgrey", "gray", "grey",
                           "darkgray", "darkgrey", "silver", "lightgray",
                           "lightgrey", "gainsboro", "whitesmoke", "white",
                           "snow", "antiquewhite", "azure", "honeydew",
                           "beige", "cornsilk"]
        colors = mcolors.CSS4_COLORS.keys()
        colors = [c for c in colors if c not in colors_excluded]
        colors.reverse()
        self.colors = colors
        return colors

    def update(self, nframe):
        """Update the cell tracks

        Args:
            nframe (int): Frame number.

        """
        self.history = self.tobj.tracks.loc[:nframe]
        self.current = self.tobj.tracks.loc[nframe]
        if not self.persist:
            dead_cells = [
                key for key in self.cell_color.keys()
                if key not in self.current.index.get_level_values("uid")
                ]
            self.color_stack.extend(self.cell_color[dead_cells])
            self.cell_color.drop(dead_cells, inplace=True)

    def _check_uid(self, uid):
        """Check tracer color

        Args:
            uid (str): Tracer ID.

        """
        if uid not in self.cell_color.keys():
            try:
                self.cell_color[uid] = self.color_stack.pop()
            except IndexError:
                self.color_stack += self.colors * 5
                self.cell_color[uid] = self.color_stack.pop()

    def plot(self, ax):
        """Plot tracers

        Args:
            ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Current
                matplotlib/cartopy axis.

        """
        for uid, group in self.history.groupby(level="uid"):
            self._check_uid(uid)
            tracer = group[["lon", "lat"]]
            if self.persist or (uid in self.current.index):
                coords = ax.projection.transform_points(ccrs.Geodetic(),
                                                        tracer.lon.values,
                                                        tracer.lat.values)
                ax.plot(coords[:, 0], coords[:, 1], "white", linewidth=5)
                ax.plot(coords[:, 0], coords[:, 1], self.cell_color[uid],
                        linewidth=3)
