.. _Configuration:

Configuration
=============

Most scripts make use of a yaml configuration file that defines some settings, such as the time
that is processed or the path to the data or data paths. The path to this configuration yaml file is
usually defined as a global variable in the beginning of the script. Please adjust this path
if necessary. At the bottom of this page you can find an example of such a configuration yaml file.
This configuration file includes data paths to several different data sources and paths to the
corresponding database files, where meta data is saved to access the data by sql queries.

.. code:: yaml

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Paths
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # General data paths
    data:
        WRF: /project/meteo/work/Gregor.Koecher/icepolcka/data/wrf/
        RG: /project/meteo/work/Gregor.Koecher/icepolcka/data/rg/
        RF: /project/meteo/work/Gregor.Koecher/icepolcka/data/rf/
        RFOut: /scratch/g/Gregor.Koecher/icepolcka/data/rf_out/
        CRSIM: /project/meteo/work/Gregor.Koecher/icepolcka/data/crsim/
        CRSIMOut: /scratch/g/Gregor.Koecher/icepolcka/data/crsim_out/
        TEMP: /project/meteo/work/Gregor.Koecher/icepolcka/data/temp/
        HMC: /project/meteo/work/Gregor.Koecher/icepolcka/data/hmc/
        DWD: /archive/meteo/external-obs/dwd/radar/c_band_isen_20190401-20201031/extracted/

    # Data base SQL files
    database:
        WRF: /home/g/Gregor.Koecher/icepolcka/db/wrf.db
        RG: /home/g/Gregor.Koecher/icepolcka/db/rg.db
        RF: /home/g/Gregor.Koecher/icepolcka/db/rf.db
        CRSIM: /home/g/Gregor.Koecher/icepolcka/db/crsim.db
        TEMP: /home/g/Gregor.Koecher/icepolcka/db/temp.db
        HMC: /home/g/Gregor.Koecher/icepolcka/db/hmc.db
        DWD: /home/g/Gregor.Koecher/icepolcka/db/dwd.db

    # Output paths
    output:
        HIW: /scratch/g/Gregor.Koecher/icepolcka/output/hiw/
        PLOTS: /scratch/g/Gregor.Koecher/icepolcka/plots/
        PSD: /scratch/g/Gregor.Koecher/icepolcka/output/psd/

    # Path to data masks (Distance and Height mask)
    masks:
        Distance: /project/meteo/work/Gregor.Koecher/icepolcka/masks/distance_mask.npy
        RF: /project/meteo/work/Gregor.Koecher/icepolcka/masks/rf.npy

    # Path to hmc cluster_file:
    hmc_cluster: /home/g/Gregor.Koecher/icepolcka/hmc_pejcic/clu.pkl


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Script settings
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Config for the CR-SIM simulation script
    crsim:
        workdir: /project/meteo-scratch/Gregor.Koecher/cluster/jobs_crsim/
        exe: /project/meteo/work/met-wrf-chem/crsim-3.33/bin/crsim
        params: /project/meteo/work/Gregor.Koecher/icepolcka/crsim/parameters/

    # Config for the shrink data script
    shrink:
        workdir: /project/meteo-scratch/Gregor.Koecher/cluster/jobs_shrink/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/shrink_data.py

    # Config for the temp script
    temp:
        workdir: /scratch/g/Gregor.Koecher/cluster/jobs_temp/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/itp_temp.py

    # Config for hydrometeor classification
    hmc:
        workdir: /scratch/g/Gregor.Koecher/cluster/jobs_hmc/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/hmc.py

    # Config for the radar filter script
    rf:
        workdir: /scratch/g/Gregor.Koecher/cluster/jobs_rf/
        folder: /project/meteo/work/met-wrf-chem/radar_filter_v1.2.1/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/rf.py

    # Config for the RegularGrid interpolation script
    rg:
        workdir: /scratch/g/Gregor.Koecher/cluster/jobs_rg/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/rg.py

    # Config for hiw statistics
    hiw:
        workdir: /scratch/g/Gregor.Koecher/cluster/jobs_hiw/
        script: /home/g/Gregor.Koecher/icepolcka/scripts/methods/high_impact_weather.py



    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Grids
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Spherical radar grid definition
    sphere:
        Isen:
            max_range: 144000
            range_res: 250
            min_az: 0
            max_az: 360
            elevs: [0.5, 0.8, 1.5, 2.5, 3.5, 4.5, 5.5, 8, 12, 17, 25]
    # Cartesian Grid settings
    cart_grid:
        z_max: 15000 # Maximum height [m] of Cartesian grid.
        z_min: -100  # Maximum height [m] of Cartesian grid.
        vert_res: 100  # Vertical resolution [m] of Cartesian grid.


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Constants
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Radar site coordinates (lon, lat, alt)
    sites:
        Isen: [12.101779, 48.17405, 678]


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # HIW Statistics
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Height indices for HIW statistics
    wrf_hgt: 0
    hmc_hgt: 16

    # Mixing ratio thresholds for hiw statistics (kg/kg)
    q_threshs: [0.000001, 0.00001, 0.0001, 0.001, 0.01]


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Plotting
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Legend names
    legend:
        8: Thompson 2-mom
        28: Thompson aerosol-aware
        10: Morrison 2-mom
        30: Spectral Bin
        50: P3
        DWD: Observation
        Obs: Observation


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # General Configs
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    start: '29.04.2019 00:00:00'  # Starting date (dd.mm.yyyy HH:MM:SS)
    end: '12.10.2020 23:59:59'  # Ending date (dd.mm.yyyy HH:MM:SS)
    date: '29.04.2019'  # Ending date (dd.mm.yyyy HH:MM:SS)
    update: False
    recheck: False
    radar: Isen
    mp: 8
    source: MODEL
    exe: /home/g/Gregor.Koecher/anaconda3/envs/ice/bin/python
