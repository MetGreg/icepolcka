# IcePolCKa

This is the repository intended for software used in the PhD project of Gregor
Köcher that is part of the project "Investigation of the initiation of
convection and the evolution of precipitation using simulations and
polarimetric radar observations at C- and Ka-band" (IcePolCKa). In this
project, polarimetric radar observations are used to evaluate weather
simulations using varying cloud microphysics schemes. A corresponding
publication is to be submitted under the name: "Convective cloud microphysics
in dual-wavelength polarimetric radar observations and numerical weather model:
methods and examples".


## Structure
The repository consists of the 'icepolcka_utils' package that has a lot of
useful utilty functions and classes to read from the data base or do some
mathematical, meteorological or other calculations/transformations. There is
then a 'script' folder that is subdivided into three categories: 'plots',
'analysis' and 'methods'. The methods folder contains all scripts that have
been applied in a methodology chain to make our model output comparable to the
radar observations. The analysis folder calculates some analysis products, such
as Contoured Frequency by Altitude Distributions (CFADs). The plots folder
contains all scripts that were used to create plots for publications.

## Configuration
Most scripts read from a configuration file that defines some settings, e.g.
the time range of data to be used. The configuration file must be located in an
"icepolcka" subdirectory within the systems default configuration folder
(~./config for linux). The name of the configuration file must be
"method_paper.yaml". An example configuration file is located within this
repository.

## SQL Data base
The scripts access data via an SQL type of data base. If this data base does
not exist yet, it will be created which can take some time, depending on the
amount of data.

## Regarding the data
All of the software in this repository relies heavily on the underlying data.
Without radar and/or model output data, none of the code in this repository will be useful.
