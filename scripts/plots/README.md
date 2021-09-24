# Plotting scripts
This folder includes all scripts used for the images that are shown in the
publication. Some plotting scripts only work if the analysis scripts have been
executed before that calculate the underlying result that is visualized. This
includes the plot_cfads.py and plot_precip_hist.py scripts.

## plot_cell_statistics.py
This plots some cell characteristics as histograms.

## plot_cfads.py 
This plots Contoured Frequency by Altitude Distributions (CFADs) as a panel
plot. The CFADs are loaded from an array that must be precalculated by the
corresponding analysis script.

## plot_domain_setup.py
Visualizes the domain and radar locations and ranges.

## plot_precip_hist.py
Plots a histogram of simulated WRF precipitation. This precip is loaded from a
json file that must be precalculated by the corresponding analysis script.

## plot_tracks.py
Visualizes cell tracks from the CellTracks data.
