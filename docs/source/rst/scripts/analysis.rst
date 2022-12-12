.. _Analysis:

Analysis scripts
================
All scripts that are used for any kind of analysis are described here. These scripts
are all located in the icepolcka/scripts/analysis folder. Some plots prepare data by calculating
statistics, some plot the results. Find below a description for each

get_psd.py
----------
This script calculates mean rain particle size distributions for a given time period. The
particle size distributions follow the corresponding microphysics scheme. The average particle size
distributions are calculated multiple times, for varying mixing ratio thresholds as defined in the
beginning of the script in the global variable 'Q_THRESHS'.

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **data: WRF**
      - The wrf data path
    * - **database: WRF**
      - The wrf database file path
    * - **output: PSD**
      - The output path
    * - **masks: Distance**
      - Path to the distance mask
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **update**
      - Whether to update the database with new files


run_hiw.py
----------
This script calculates high impact weather statistics for hail/graupel and rain. This includes
frequency and area of rain and hail/graupel events of varying event strength, for WRF model data
and hmc classified data. The analysis happens at a specific height, the index of this height must
be given in the configuration file. The script is designed to work on a daily basis: the start- and
end time must always be from 00:00:00 to 23:59:59.

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/analysis/cluster/high_impact_weather.py . The path to this
script must be given in the configuration file.

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **data: RG**
      - The rg data path
    * - **database: RG**
      - The rg database file path
    * - **data: HMC**
      - The hmc data path
    * - **database: HMC**
      - The hmc database file path
    * - **data: WRF**
      - The wrf data path
    * - **database: WRF**
      - The wrf database file path
    * - **output: HIW**
      - The output path
    * - **masks: RF**
      - The path to the rf mask
    * - **masks: Distance**
      - The path to the distance mask
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **update**
      - Whether to update the database with new files
    * - **exe**
      - The python executable
    * - **hiw: workdir**
      - The cluster working directory
    * - **hiw: script**
      - The actual python script the is executed from the cluster
    * - **wrf_hgt**
      - The height index, at which the WRF data is analysed
    * - **hmc_hgt**
      - The height index, at which the HMC data is analysed


plot_psd.py
-----------
This script plots the particle size distributions that were calculated by get_psd.py . The script
finds the precalculated data by the time information in the configuration file. This information
must exactly match (start- and end-time must exactly match the precalculated time range).

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **output: PSD**
      - The path to the precalculated PSD data
    * - **output: PLOTS**
      - The output path
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)


plot_rg_panel.py
----------------
Plots a panel plot of RG reflectivity data for a given time. The panel plot consists of model
data from the 5 different MP-scheme simulations and the corresponding radar data.

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **data: RG**
      - The rg data path
    * - **database: RG**
      - The rg database file path
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **update**
      - Whether to update the database with new files


plot_hmc_panel.py
-----------------
Plots a panel plot of hydrometeor classification data for a given time. The panel plot consists of
model data from the 5 different MP-scheme simulations and the corresponding radar data.

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **data: RG**
      - The rg data path
    * - **database: RG**
      - The rg database file path
    * - **data: HMC**
      - The hmc data path
    * - **database: HMC**
      - The hmc database file path
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **update**
      - Whether to update the database with new files


plot_hiw_panel.py
-----------------
Plots a panel plot of precalculated hiw statistics. The panel plot consists of reflectivity based
statistics at 1 km altitude in the top row, mixing ratio based statistics at 1 km altitude in the
center row and mixing ratio based statistics at the surface in the bottom row. The left column is
the frequency of heavy rain or hail/graupel events for varying event strengths and the right column
is the area of these events.

In the configuration file, the following information must be given:

.. list-table::
    :widths: 10 50
    :header-rows: 0

    * - **output: HIW**
      - The path to the precalculated hiw statistics
    * - **start**
      - Start time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
    * - **end**
      - End time (UTC) of the data to be processed (format %d.%m.%Y %H:%M:%S)
