.. _Installation:

Installation
=============

The code is almost completely based on python. It is recommended to do the installation of all
python packages via anaconda:
https://www.anaconda.com/products/distribution .

Please install anaconda first, before continuing with the steps below.

Follow these steps to install the icepolcka package and all dependencies from scratch within a new
python environment. It is assumed that you have downloaded the icepolcka folder, either from zenodo,
or from gitlab. Execute the commands from within the icepolcka folder.

#. conda create -y --name ice_env
#. conda activate ice_env
#. conda config --add channels conda-forge
#. conda install -y --file requirements.txt
#. cd icepolcka_utils
#. python setup.py install

.. note::
    If you don't want to use anaconda for installation, you should also be able to use pip, but this
    was not tested.

