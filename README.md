# IcePolCKa


## Installation
Almost all code is written in python. It is recommended to use anaconda to install python packages:
https://www.anaconda.com/products/distribution .

Follow these steps to install the icepolcka package and all dependencies from scratch within a new 
python environment with anaconda. Execute the commands from within the top level icepolcka folder.

1. conda create -y name ice_env
2. conda activate ice_env
3. conda config --add channels conda-forge
4. conda install -y -file requirements.txt
5. cd icepolcka_utils
6. python setup.py install

## Documentation
All documentation, including installation and configuration as well as code documentation is 
done via sphinx. Create the sphinx autodocumentation with the following code from the top level
directory:

```
    make doc
```

The documentation will be created at:

    icepolcka/docs/build/index.html

Open this file with any browser to see the documentation.

> **Note**
> Sometimes, red warnings are shown. Not always this breaks the documentation. Check the index.html
> file in any case.
