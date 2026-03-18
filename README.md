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
There is a banksim example that uses pyjevsim's DEVS functionality and journaling features.
[documentation](link)

## Execution Modes

SysExecutor supports three execution modes via `ExecutionType`:

| Mode | Description |
|------|-------------|
| `V_TIME` | Virtual time — simulation runs as fast as possible |
| `R_TIME` | Real time — simulation paces itself to wall-clock time |
| `HLA_TIME` | HLA/RTI-controlled time — time advancement is driven externally |

```python
from pyjevsim.system_executor import SysExecutor
from pyjevsim.definition import ExecutionType

se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
```

## Multi-threading Support

SysExecutor provides thread-safe APIs for multi-threaded simulation environments where external threads inject events while the simulation runs.

### Pause / Resume

Pause the simulation to allow external threads to accumulate events, then resume.

```python
se.pause_sim()    # Pauses the simulation loop
# External threads can safely call insert_external_event() while paused
se.resume_sim()   # Resumes the simulation loop
```

### External Event Injection

Insert events from external threads into the simulation. Thread-safe via internal synchronization.

```python
se.insert_external_event("port_name", message, scheduled_time=0)
```

### Output Event Callback

Register a callback to be notified when output events are generated, avoiding polling.

```python
se.set_output_event_callback(lambda: print("output ready"))
events = se.handle_external_output_event()
```

## HLA/RTI Integration (HLA_TIME Mode)

For HLA/RTI-controlled simulations, use `HLA_TIME` mode with `step()` and `get_next_event_time()`.

```python
se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
se.register_entity(model)
se.init_sim()

# RTI-driven loop
while not se.is_terminated():
    next_time = se.get_next_event_time()
    # ... request time advance from RTI, wait for grant ...
    granted_time = ...  # time granted by RTI
    output_events = se.step(granted_time)
    # ... publish output_events to RTI ...
```

### `step(granted_time)`
Executes one simulation step up to the granted time. Returns output events generated during the step.

### `get_next_event_time()`
Returns the earliest scheduled event time (internal or external). Used to determine the Time Advance Request value for the RTI.

## Graceful Termination

```python
se.terminate_simulation()  # Sets SIMULATION_TERMINATED state
se.is_terminated()         # Returns True if terminated
```

Signal handlers (SIGTERM, SIGINT) automatically invoke `terminate_simulation()` on all registered SysExecutor instances.

## License   
Author: Changbeom Choi (@cbchoi)   
Copyright (c) 2014-2020 Handong Global University      
Copyright (c) 2021-2024 Hanbat National University    
License: MIT.  The full license text is available at:   
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE   
