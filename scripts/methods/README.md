# Method scripts

Here you can find all scripts used for the methodology chain of icepolcka:

## Masks
- save_distance_mask.py calculates a mask for the model domain. All grid boxes
  outside of the Mira-35 radar range are masked.
- save_height_mask.py calculates a mask for each radar, where all grid boxes
  above the highest or below the lowest beam of a volume scan are masked.

## Beam intersection
- calc_intersection.py precalculates the intersection of Mira-35 and Poldirad
  beams for a number of azimuth, range combinations.
 

## CR-SIM output
The CR-SIM output is very large and needs postprocessing.
- shrink_data.py removes uneccessary variables and masks grid boxes outside of
  the Mira-35 range.
- readd_radar_specifics.py brings the data into a format for the next step in
  the methodology chain: radar_filter.py

## Transformation to radar grid
- rf.py transforms data on a Cartesian grid to a spherical radar grid.

## RF output
- The radar_filter writes files for each variable separately. The script
  merge_rf.py merges these files to single files for each time step.

## RegularGrid
The cell tracking only works on regular Cartesian Grid data.
- rg.py transforms the spherical radar data to a regular Cartesian grid.

## Cell tracking
- track_cells.py applies the TINT cell tracking on RegularGrid data.

## Cluster
Some scripts (rf.py, rg.py, shrink_data.py) are supposed to run on the cluster
to make it possible to process multiple time steps at once. The corresponding
scripts that start the cluster jobs are lcoated in the subfolder 'cluster'.

## Order of execution
Since this is mostly a chain of methodology steps, the order is important. When
running the complete chain, the order should be:

1) Calculate masks and beam intersections:
    1.1) ./calc_intersection.py
    1.2) ./save_height_mask.py
    1.3) ./save_distance_mask.py
2) ./cluster/run_crsim.py
3) ./cluster/run_shrink.py
4) ./readd_radar_specifics.py
5) ./cluster/rf.py
6) ./merge_rf.py
7) ./cluster/run_rg.py
8) ./track_cells.py
