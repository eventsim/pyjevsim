# pyjevsim
## Introduction
pyjevsim is a DEVS(discrete event system specification) environment that provides journaling functionality.
It provides the ability to snapshot and restore models or simulation engines.
It's compatible with Python versions 3.10+.
   
For more information, see the documentation. : [pyjevsim](https://pyjevsim.readthedocs.io/en/latest/index.html)
   
## Installing
You can install pyjevsim via
```
git clone https://github.com/eventsim/pyjevsim
```
   
## Dependencies
The only dependency required by pyjevsim is dill ~= 0.3.6 for model serialization and restoration.  
dill is an essential library for serializing models and simulation states and can be installed via. 
```
pip install dill
```
   
### Optional Dependencies
pytest is an optional dependency required for running test cases and example executions. 
You can install pyjevsim via
```
pip install pytest
```
   
Additionally, you can install all necessary libraries, including optional dependencies, by running the following command:
```
pip install -r requirements.txt
``` 

## Working with pyjevsim
Once you have installed the library, you can begin working with it.

### Quick Start
The docs describe how to configure a simulation via pyjevsim's BehaviorModel and SysExecutor.
Check out the [documentation](link) to configure your simulation.

### Example
There is a banksim example that uses pyjevsim's DEVS functionality and jouranling features.
[documentation](link)

## License
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE