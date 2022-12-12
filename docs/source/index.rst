Welcome to the Documentation of IcePolCKa!
==========================================

This is the documentation for the repository of IcePolCKa. IcePolCKa is a research project within
PROM in collaboration between the DLR in Oberpfaffenhofen and the LMU in Munich. The main
contributors to this repository are Eleni Tetoni (eleni.tetoni@dlr.de) and Gregor Köcher
(gregor.koecher@lmu.de).

Installation
------------
For installation, follow this guide: :ref:`installation`.


Configuration
-------------
Before you start using this repository, make sure to have the correct configuration. How to
configure your setup is described in :ref:`configuration`.


Testing
-------
There are automatic unittests available. To see if everything works as expected, they should be
executed in the beginning. Find a guide on the tests here: :ref:`testing`.


Scripts
-------
There are plenty of executable scripts available, to process, analyze and plot the data. Some
explanation about these scripts is documented here: :ref:`scripts`.


Icepolcka package
-----------------
The majority of the code is available as a python package. The sphinx auto-documentation for this
package can be found here: :doc:`icepolcka_utils <rst/icepolcka_utils/modules>`.


.. toctree::
   :maxdepth: 1
   :caption: Contents:

   rst/installation
   rst/configuration
   rst/testing
   rst/scripts
   rst/icepolcka_utils/modules


.. autosummary::
   :toctree: _autosummary
   :recursive:

   ../../icepolcka_utils/icepolcka_utils


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
