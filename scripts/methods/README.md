# Data processing scripts

All scripts that are used for any kind of data processing are described here. These scripts
are all located in this icepolcka/scripts/methods folder. For a complete data process starting from
the WRF output to the final hydrometeor classification, the scripts should be executed in the
following order:

1. save_distance_mask.py (If distance mask does not exist yet)
2. run_crsim.py
3. run_shrink.py
4. run_rf.py
5. merge_rf.py
6. run_rg.py
7. save_rf_mask.py (If rf mask does not exist yet)
8. apply_rf_mask.py
9. run_itp_temp.py
10. run_hmc.py

Find a section for each of these scripts below that explains how to execute it and what it does.
Almost all scripts access a configuration yaml file, that defines some required information, such
as the data paths. See the :ref:`configuration` page for an example configuration file. The path
to this file is given as a global variable in the beginning of each script and must be adjusted.


## save_distance_mask.py
The Munich domain is 360 x 360 pixel big. The analysis happens on the inner third of this domain, to
exclude any potential boundary issues. Most scripts mask everything outside this inner third by
applying a mask that was saved before. This script creates this mask. It just calculates the
distance of each model grid box to the center. If it exceeds 24 km (third of the domain), the
corresponding mask entry is put to True. This script needs to be executed only once, given that
the domain grid does not change. The grid information is taken from a WRF file. The distance to
the center is calculated by accessing the location of the Mira radar (which is by definition in the
center of the model). The distance to this center that shall be used for analysis is defined in the
configuration file (Recommended is 24000, which equals one third of the domain).

In the configuration file, the following information must be given:


| Variable            | Description                            |
|---------------------|----------------------------------------|
| **masks: Distance** | Output path of the mask                |
| **sites: Mira35**   | Mira radar location (lon, lat, alt)    |
| **r_max**           | Maximum allowed distance to center (m) |


## run_crsim.py
This script executes the CR-SIM radar forward operator on a WRF output file, as configured in the
configuration yaml file. For this to work, the CR-SIM radar forward operator must have been
installed. You can find the code and installation instructions here:
https://you.stonybrook.edu/radar/research/radar-simulators/

The radar forward operator simulates a specific radar. The radar specifics are given in a parameter
file. The specifics for the Isen radar are given in the folder:
icepolcka/crsim/parameters/

---
**NOTE**

The PARAMETER file that corresponds to the input configuration is
searched within the params-folder. The PARAMETER files must be saved in
specific sub folders (X denotes the WRF ID of the MP scheme):

params/MPX/radar/PARAMETERS

---

The script looks for a WRF file from which reflectivity will be simulated.  The WRF file is found
from the specified configuration.

The script is sending a job to the SLURM cluster.

In the configuration file, the following information must be given:


| Variable              | Description                                                      |
|-----------------------|------------------------------------------------------------------|
| **data: CRSIMOut**    | The CR-SIM output path                                           |
| **data: WRF**         | The wrf data path                                                |
| **database: WRF**     | The wrf database file path                                       |
| **start**             | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**               | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**                | MP scheme of the data to be processed                            |
| **radar**             | Name of the radar to be simulated                                |
| **update**            | Whether to update the database with new data (bool)              |
| **crsim: workdir**    | The cluster working directory                                    |
| **crsim: exe**        | The CR-SIM executable                                            |
| **crsim: parameters** | The CR-SIM parameter file locations                              |


## run_shrink.py
The CRSIM data is very big. Since most analysis happens on the inner third of the Munich domain,
all data outside is masked by this script. For this, the distance masked created by
'save_distance_mask.py' is utilized. Also, everything above a specified height is masked
(Recommended is 15000 m). The script looks through the CRSIMOut data path, opens each data file,
masks everything outside the inner third and saves the masked field to the CRSIM output path as
given in the configuration file. The CRSIMOut must be of a very specific structure:

data_path/MP?/radar_name/YYYY/MM/DD/

where the ? is the corresponding MP-scheme. If the CR-SIM output files have been created with the
'run_crsim.py' script, the CRSIMOut files are automatically saved in this format. The 'run_shrink'
script sends a job to the cluster, which then executes the actual script to shrink the data. The
location of this script must be given in the configuration file. Default location is at
icepolcka/scripts/methods/cluster/shrink_data.py

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/methods/cluster/shrink_data.py . The path to this
script must be given in the configuration file.

In the configuration file, the following information must be given:

| Variable             | Description                                                      |
|----------------------|------------------------------------------------------------------|
| **data: CRSIMOut**   | Unprocessed CR-SIM data path                                     |
| **data: CRSIM**      | Output path for shrinked CR-SIM data                             |
| **start**            | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**              | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**               | MP scheme of the data to be processed                            |
| **radar**            | Name of the radar to be simulated                                |
| **exe**              | The python executable                                            |
| **shrink: workdir**  | The cluster working directory                                    |
| **shrink: script**   | The actual python script that is executed from the cluster       |
| **masks: Distance**  | The location of the distance mask                                |
| **cart_grid: z_max** | The maximum height (m) of the grid                               |


## run_rf.py
The CR-SIM output data is available on the same grid as the input WRF model data. For a fair
comparison to real radar data, the data must hence be transformed to a spherical radar grid. This is
what the radar_filter script does, which is available from the same website as the CR-SIM code:
https://you.stonybrook.edu/radar/research/radar-simulators/

The grid of the radar to be simulated must be specified under 'sphere' in the configuration file.
For example, for the DWD Isen radar:


* sphere:
  * Isen:  
    * max_range: 144000
    * min_az: 0
    * max_az: 360
    * elevs: [0.5, 0.8, 1.5, 2.5, 3.5, 4.5, 5.5, 8, 12, 17, 25]

where max_range is the maximum range of the radar in m, min_az and max_az are the minimum and
maximum azimuth angles to be simulated and elevs is a list of the elevation angles that are to be
simulated.

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/methods/cluster/rf.py . The path to this script must be given
in the configuration file.

In the configuration file, the following information must be given:

| Variable             | Description                                                      |
|----------------------|------------------------------------------------------------------|
| **data: RFOut**      | The rf output path                                               | 
| **data: CRSIM**      | The CR-SIM data path                                             |
| **database: CRSIM**  | The CR-SIM database file path                                    |
| **start**            | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**              | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**               | MP scheme of the data to be processed                            |
| **radar**            | Name of the radar to be simulated                                |
| **update**           | Whether to update the database with new data (bool)              |
| **exe**              | The python executable                                            |
| **rf: workdir**      | The cluster working directory                                    |
| **rf: script**       | The actual python script that is executed from the cluster       |
| **rf: folder**       | The folder where the radar_filter code is located                |
| **sphere**           | Radar grid specifics (see explanation above)                     |


## merge_rf.py
The run_rf.py script creates a new file for each of the polarimetric variables. For easier access
to the data, the merge_rf.py script merges these files into one single file per time step.
Furthermore, attenuated reflectivity ('Zhh_corr') and attenuated differential reflectivity
('Zdr_corr') is calculated, by summing up simulated attenuation and simulated differential
attenuation along the beam path and subtracting this from the unattenuated reflectivity.

The script expects the rf output data to be located in the given data_path in subdirectories of the
following structure:
data_path/MP?/radar_name/YYYY/MM/DD/

with YYYY, MM, DD the year, month and day respectively and ? the WRF ID of the MP scheme (which can
be single or double-digit). When the rf output data was calculated from the run_rf.py script, the
data is automatically in this format.

By design of the script, it works currently only for a time range of 1 day at maximum.

In the configuration file, the following information must be given:

| Variable            | Description                                                      |
|---------------------|------------------------------------------------------------------|
| **data: RFOut**     | Unprocessed rf output data path                                  | 
| **data: RF**        | Output for merged rf data                                        |
| **start**           | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**             | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**              | MP scheme of the data to be processed                            |
| **radar**           | Name of the radar to be simulated                                |


## run_rg.py
Later analysis usually happens on a Cartesian Grid. This script transforms all data (radar data or
model data after applying the radar_filter) to a regular Cartesian grid that is specified in the
configuration file. For example:

* cart_grid:
  * z_min: -100
  * z_max: 15000
  * vert_res: 100

Where z_min and z_max are the minimum and maximum height (m) of the grid above mean sea level at
the grid origin (which is at the radar site to be processed) and vert_res is the vertical
resolution (m). Negative values for z_min can make sense, due to earth curvature.

The data is interpolated to this regular Cartesian grid by applying an inverse distance weight
interpolation, i.e., the four nearest data points are weighted by their distance to the target
grid point. This script works for both, model and DWD data. Since the input data is of different
format, the functions that are invoked for reading the data are a little different. The DWD KDP
data is smoothed over 5 km with a running mean, because observed KDP is noisy. The output files
are exactly of the same format, independent of the input data.

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/methods/cluster/rg.py . The path to this script must be given
in the configuration file.

In the configuration file, the following information must be given:


| Variable        | Description                                                                |
|-----------------|----------------------------------------------------------------------------|
| **data: RG**    | The rg output path                                                         | 
| **start**       | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)           |
| **end**         | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)             |
| **mp**          | MP scheme of the data to be processed                                      |
| **radar**       | Name of the radar to be simulated                                          |
| **source**      | The input data source ('MODEL' or 'DWD')                                   |
| **update**      | Whether to update the database with new data (bool)                        |
| **exe**         | The python executable                                                      |
| **rg: workdir** | The cluster working directory                                              |
| **rg: script**  | The actual python script that is executed from the cluster                 |
| **cart_grid**   | Cartesian grid specifics (see explanation above)                           |
| **sites**       | Site coordinates (lon, lat, alt) of simulated radar (e.g., 'sites: Isen')  |

If the data source is 'MODEL':

| Variable         | Description                                                      |
|------------------|------------------------------------------------------------------|
| **data: RF**     | The rf data path                                                 |
| **database: RF** | The rf database file path                                        |
| **mp**           | MP scheme of the data to be processed                            |

If the data source is 'DWD':


| Variable          | Description                           |
|-------------------|---------------------------------------|
| **data: DWD**     | The DWD data path                     |
| **database: DWD** | The DWD database file path            |


## save_rf_mask.py
The radar_filter code seems to rotate the grid very slightly. To correctly mask the data that is
used after applying the radar_filter code, this script saves a mask that is adjusted to this
rotation. It works by loading an RG-file and look at the ZDR-field, which was masked exactly to the
Mira-35 range before the RF-transformation. This script simply saves the resulting NaN-field. The
path to this RG file is given in the beginning of the script as a global variable and must be
adjusted. The script must be executed only once, as long as the grid does not change.

In the configuration file, the following information must be given:


| Variable          | Description                    |
|-------------------|--------------------------------|
| **masks: RF**     | The output path of the rf mask |


## apply_rf_mask.py
This applies the rf mask saved by the 'save_rf_mask.py' script to RG data. The data is overwritten,
because the reason behind the masking is to save disk space.

In the configuration file, the following information must be given:


| Variable         | Description                                         |
|------------------|-----------------------------------------------------|
| **data: RG**     | The rg data path                                    | 
| **database: RG** | The rg database file path                           |
| **mp**           | MP scheme of the data to be processed               |
| **radar**        | Name of the radar to be simulated                   |
| **source**       | The input data source ('MODEL' or 'DWD')            |
| **update**       | Whether to update the database with new data (bool) |
| **masks: RF**    | The output path of the rf mask                      |


## run_itp_temp.py
For later applications (e.g., the hydrometeor classification) temperature fields are required. This
script interpolates the original model temperature to the regular Cartesian grid, the same as used
for the RG files. The interpolation makes use of an inverse distance weight, the same method as used
for the RG interpolation.

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/methods/cluster/itp_temp.py . The path to this script must be
given in the configuration file.

In the configuration file, the following information must be given:

| Variable            | Description                                                      |
|---------------------|------------------------------------------------------------------|
| **data: RG**        | The rg data path                                                 | 
| **database: RG**    | The rg database file path                                        |
| **data: WRF**       | The wrf data path                                                | 
| **database: WRF**   | The wrf database file path                                       |
| **data: CRSIM**     | The CR-SIM data path                                             | 
| **database: CRSIM** | The CR-SIM database file path                                    |
| **data: TEMP**      | The temperature data path                                        | 
| **masks: RF**       | The path to the rf mask                                          |
| **start**           | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**             | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**              | MP scheme of the data to be processed                            |
| **radar**           | Name of the radar to be simulated                                |
| **source**          | The input data source ('MODEL' or 'DWD')                         |
| **update**          | Whether to update the database with new data (bool)              |
| **exe**             | The python executable                                            |
| **temp: workdir**   | The cluster working directory                                    |
| **temp: script**    | The actual python script that is executed from the cluster       |



## run_hmc.py
This runs a hydrometeor classification algorithm based on the regular grid data and the interpolated
temperature field. The classification algorithm is from Dolan et al, 2013. It will always take the
temperature field of the simulation with MP-ID 8 (Thompson 2-mom), because the temperature does not
change much between the microphysics schemes simulations (this is assumed).

The script is sending a job to the SLURM cluster. The cluster job executes another python script,
which is located at icepolcka/scripts/methods/cluster/hmc.py . The path to this script must be
given in the configuration file.

In the configuration file, the following information must be given:


| Variable           | Description                                                      |
|--------------------|------------------------------------------------------------------|
| **data: RG**       | The rg data path                                                 | 
| **database: RG**   | The rg database file path                                        |
| **data: TEMP**     | The temperature data path                                        | 
| **database: TEMP** | The temperature database file path                               |
| **data: HMC**      | The output path                                                  | 
| **start**          | Start time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S) |
| **end**            | End time (UTC) of the data to be processed (%d.%m.%Y %H:%M:%S)   |
| **mp**             | MP scheme of the data to be processed                            |
| **radar**          | Name of the radar to be simulated                                |
| **source**         | The input data source ('MODEL' or 'DWD')                         |
| **update**         | Whether to update the database with new data (bool)              |
| **exe**            | The python executable                                            |
| **hmc: workdir**   | The cluster working directory                                    |
| **hmc: script**    | The actual python script that is executed from the cluster       |

