"""Create color maps"""
import numpy as np
import matplotlib.colors as mcolors


def get_precip_cmap():
    """Create a precipitation colormap

    Returns:
        matplotlib.colors.ListedColormap:
            Colormap for precipitation plots.

    """
    blues = mcolors.LinearSegmentedColormap.from_list(
        "blues", ["lightblue", "darkblue"]
        )
    greens = mcolors.LinearSegmentedColormap.from_list(
        "greens", ["lightgreen", "darkgreen"]
        )
    reds = mcolors.LinearSegmentedColormap.from_list(
        "reds", ["yellow", "orange", "red", "darkred"]
        )
    stacked_colors = np.vstack(
        (blues(np.linspace(0, 1, 64)), greens(np.linspace(0, 1, 64)),
         reds(np.linspace(0, 1, 128)), np.array([[1, 0.7, 1, 1]]))
        )
    cmap = mcolors.ListedColormap(stacked_colors)
    return cmap
