"""Plot domain setup

The domain extent, the radar locations, the radar range and a visualization
of the radar RHI scans are plotted onto a background image of Munich. Some
configuration settings are loaded from a configuration file.

For an explanation on how to use the configuration file, see the README file.

"""
import numpy as np
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import mark_inset

from icepolcka_utils.data_base import WRFDataBase
from icepolcka_utils.geo import get_pos_from_dist
from icepolcka_utils.plots import create_figure, plot_background, add_grid, \
    add_features, add_cities
from icepolcka_utils.utils import load_config


def get_wrf_data(wrf_path, db, update, recheck):
    """Get WRF data

    Args:
        wrf_path (str): Path to WRF data.
        db (str): Path to WRF data base.
        update (bool): Whether to update the data base with new files.
        recheck (bool): Whether to recheck if files in data base have changed.

    Returns:
        xarray.core.dataset.Dataset:
            Loaded WRF data set.

    """
    print("Getting WRF data")
    with WRFDataBase(wrf_path, db, update=update, recheck=recheck) as wrf_db:
        handle = wrf_db.get_latest_data(domain="Munich")[0]
    df = handle['clouds'].load()
    return df


def plot_domain(ax, df):
    """Plot the domain

    Plots the domain with a uniform color with a low alpha value. The domain
    extent is taken from the lon/lat coordinates of the given WRF data.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis onto which
            the domain extent will be plotted.
        df (xarray.core.dataset.Dataset): WRF dataset containing lon/lat
            coordinates of the domain.

    Returns:
        cartopy.mpl.geoaxes.GeoAxes.Subplot:
            Matplotlib axis that includes the domain extent.

    """
    lons = df['XLONG'][0].values
    lats = df['XLAT'][0].values
    data = df['T'][0][0].values
    data[:] = 0
    coordinates = ax.projection.transform_points(ccrs.Geodetic(), lons, lats)
    ax.contourf(coordinates[:, :, 0], coordinates[:, :, 1], data, alpha=0.15)
    return ax


def get_radar_proj(ax, loc):
    """Get radar projection

    Transforms the radar lon/lat coordinates into the corresponding
    coordinates of the matplotlib axis projection.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxes.Subplot): Matplotlib axis that
            corresponds to the coordinate projection.
        loc (list or tuple): lon/lat of radar site.

    Returns:
        tuple:
            (x, y) coordinates of Mira-35 site in corresponding projection of
                matplotlib axis.

    """
    mira_proj = ax.projection.transform_points(
        ccrs.Geodetic(), np.array(loc[0]), np.array(loc[1])
        )[0]
    return tuple(mira_proj)


def plot_radar_range(ax, proj, loc, r, color, lw=2):
    """Plot radar range

    Visualizes the radar ranges with circles around the radar site. The
    circles have the radius of the radar range.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis onto which the
            radar range will be plotted.
        proj (tuple): (x, y) coordinates of radar site projected to matplotlib
            axis coordinates.
        loc (list or tuple): lon/lat of radar site.
        r (float): Radius of radar in m.
        color (str): Color as a HEX number that is used for the circle.
        lw (int): Line width.

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis that includes the radar setup.

    """
    lon, lat = get_pos_from_dist(loc, r, 0)
    circle = ax.projection.transform_points(ccrs.Geodetic(), np.array(lon),
                                            np.array(lat))[0]
    radius = circle[1] - proj[1]
    ax.add_patch(Circle(proj, radius, edgecolor=color, facecolor="None",
                        linewidth=lw))
    return ax


def plot_radar_loc(ax, mira_proj, poldi_proj, isen_proj=None, legend=False,
                   s=240):
    """Plot radar locations

    Visualizes the radar locations with stars of different colors.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis on which the
            image will be plotted.
        mira_proj (tuple): Mira-35 (x, y) coordinates projected to
            matplotlib axis coordinates.
        poldi_proj (tuple): Poldirad (x, y) coordinates projected to
            matplotlib axis coordinates.
        isen_proj (tuple): Isen (x, y) coordinates projected to matplotlib axis
            coordinates.
        legend (bool): If true, a legend will be drawn.
        s (int): Marker size.

    """
    ax.scatter(mira_proj[0], mira_proj[1], label="Mira-35", color="#1f77b4",
               s=s, marker="*", zorder=5)
    ax.scatter(poldi_proj[0], poldi_proj[1], label="Poldirad", color="#ff7f0e",
               s=s, marker="*", zorder=5)
    if isen_proj:
        ax.scatter(isen_proj[0], isen_proj[1], label="Isen", color="#2ca02c",
                   s=s, marker="*", zorder=5)
    if legend:
        print("Plotting legend")
        ax.legend()
    return ax


def plot_main_image(ax, extent, df, sites):
    """Plot main image

    Plots the main image, the domain over Munich, the radar locations and
    ranges.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis on which the
            image will be plotted.
        extent (list): Extent of inset (lon_min, lon_max, lat_min, lat_max).
        df (xarray.core.dataset.Dataset): WRF dataset containing the grid
            coordinates.
        sites (dict): Dictionary of radar site coordinates (lon, lat, alt).

    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis on which the main image has been plotted.

    """
    print("Plotting main image")
    ax = plot_background(ax, extent, zoom=10)
    ax = add_features(ax)
    ax = add_cities(ax, cities=["München", "Nürnberg", "Augsburg",
                                "Regensburg"])
    ax = plot_domain(ax, df)

    # Get projections
    mira_proj = get_radar_proj(ax, sites['Mira35'])
    poldi_proj = get_radar_proj(ax, sites['Poldirad'])
    isen_proj = get_radar_proj(ax, sites['Isen'])

    # Plot radar ranges and locations
    ax = plot_radar_range(ax, mira_proj, sites['Mira35'], 24000, "#1f77b4")
    ax = plot_radar_range(ax, poldi_proj, sites['Poldirad'], 120000, "#ff7f0e")
    ax = plot_radar_range(ax, isen_proj, sites['Isen'], 150000, "#2ca02c")
    plot_radar_loc(ax, mira_proj, poldi_proj, isen_proj, legend=True)

    # Add grid
    ax = add_grid(ax)

    return ax


def plot_rhi(ax, proj, loc, r, az, color):
    """Plot RHI lines

    Plots some lines to visualize RHI scans of the radar.

    Args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis onto which the
            RHI lines will be plotted.
        proj (tuple): (x, y) coordinates of radar site projected to matplotlib
            axis coordinates.
        loc (list or tuple): lon/lat of radar site.
        r (int): Range of RHI line [m].
        az (int): Azimuth angle of RHI line.
        color (str): Color as a HEX number that is used for the circle.


    Returns:
        cartopy.mpl.geoaxes.GeoAxesSubplot:
            Matplotlib axis that includes the RHI lines.

    """
    trg = get_pos_from_dist(loc, r, az)
    trg_proj = ax.projection.transform_points(
        ccrs.Geodetic(), np.array(trg[0]), np.array(trg[1])
        )[0]
    ax.plot([proj[0], trg_proj[0]], [proj[1], trg_proj[1]], color=color,
            linewidth=1.5)
    return ax


def add_rectangle(ax, extent):
    lon_min, lon_max, lat_min, lat_max = extent
    rect_ll = ax.projection.transform_points(ccrs.Geodetic(), np.array(lon_min),
                                             np.array(lat_min))[0]
    rect_ul = ax.projection.transform_points(ccrs.Geodetic(), np.array(lon_min),
                                             np.array(lat_max))[0]
    rect_lr = ax.projection.transform_points(ccrs.Geodetic(), np.array(lon_max),
                                             np.array(lat_min))[0]
    width = (rect_lr - rect_ll)[0]
    height = (rect_ul - rect_ll)[1]
    ax.add_patch(Rectangle(rect_ll, width, height, edgecolor="gray",
                           facecolor="None", linewidth=1))
    return ax


def plot_inset(fig, ax, extent, sites):
    """Plot inset

    Plots an inset into the existing main image. This inset zooms onto the
    Mira-35 domain and visualizes some RHI scans.

    Args:
        fig (matplotlib.figure.Figure): Figure of main image.
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): Matplotlib axis on which the
            image will be plotted.
        extent (list): Extent of inset (lon_min, lon_max, lat_min, lat_max).
        sites (dict): Dictionary of radar site coordinates (lon, lat, alt).

    """
    print("Plotting inset")

    ax = add_rectangle(ax, extent)
    left, bottom, width, height = [0.6, 0.1, 0.58, 0.4]
    ax2 = fig.add_axes([left, bottom, width, height], projection=ax.projection)
    ax2 = plot_background(ax2, extent, zoom=12)
    ax2 = add_features(ax2)
    ax2 = add_cities(ax2, cities=['München'])

    # Get projections
    mira_proj = get_radar_proj(ax2, sites['Mira35'])
    poldi_proj = get_radar_proj(ax2, sites['Poldirad'])

    # Plot circle around Mira-35
    ax2 = plot_radar_range(ax2, mira_proj, sites['Mira35'], 24000, "#1f77b4",
                           lw=2)

    # Plot radar location
    plot_radar_loc(ax2, mira_proj, poldi_proj, s=200)

    # Plot some RHI scans
    ax2 = plot_rhi(ax2, mira_proj, sites['Mira35'], 24000, 290, "#1f77b4")
    ax2 = plot_rhi(ax2, mira_proj, sites['Mira35'], 24000, 300, "#1f77b4")
    ax2 = plot_rhi(ax2, mira_proj, sites['Mira35'], 24000, 310, "#1f77b4")
    ax2 = plot_rhi(ax2, poldi_proj, sites['Poldirad'], 60000, 20, "#ff7f0e")
    ax2 = plot_rhi(ax2, poldi_proj, sites['Poldirad'], 60000, 30, "#ff7f0e")
    ax2 = plot_rhi(ax2, poldi_proj, sites['Poldirad'], 60000, 40, "#ff7f0e")

    # Create lines from main image to inset
    mark_inset(ax, ax2, loc1=1, loc2=3, fc="none", ec="0.5")
    return ax2


def save_plot(output):
    """Save plot

    Args:
        output (str): Path to output file.

    """
    print("Saving plot")
    plt.tight_layout()
    plt.savefig(output, bbox_inches="tight")


def main():
    print("Starting main")
    cfg = load_config()
    df = get_wrf_data(cfg['data']['WRF'], cfg['database']['WRF'], cfg['update'],
                      cfg['recheck'])
    fig, ax = create_figure()
    ax = plot_main_image(ax, cfg['extent']['Domain'], df, cfg['sites'])
    plot_inset(fig, ax, cfg['extent']['Inset'], cfg['sites'])
    save_plot(cfg['output']['DOMAIN'])


if __name__ == "__main__":
    main()
