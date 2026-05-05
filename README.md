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

### Output messages are shared by reference

When a model's output port has multiple downstream subscribers, every
subscriber receives the **same** `SysMessage` object. pyjevsim does not
deep-copy outputs during propagation — and neither does any other major
Python DEVS engine (xdevs.py and PythonPDEVS share references the same
way; `benchmark/aliasing_test.py` empirically demonstrates this for all
four engines in the comparison set). Treat received messages as
immutable; if your model needs to mutate a payload, copy it on the
receiver side:

```python
def ext_trans(self, port, msg):
    payload = list(msg.retrieve())   # local copy, safe to mutate
    payload.append(my_local_data)
    ...
```

See [`benchmark/results/ALIASING.md`](benchmark/results/ALIASING.md) for
the full investigation and per-engine source pointers.

## Benchmarks

The [`benchmark/`](benchmark/) directory contains a DEVStone suite plus
adapters that run the same workload against other Python DEVS engines so the
pyjevsim baseline can be tracked over time.

```
benchmark/
├── devstone/                     # original pyjevsim-only DEVStone (flat)
│   ├── atomic.py
│   └── topology.py
├── engines/                      # cross-engine canonical DEVStone
│   ├── common.py                 # shared RunResult dataclass
│   ├── pyjevsim/                 # adapter for this repo
│   ├── xdevs/                    # adapter for xdevs.py (pip install xdevs)
│   ├── pypdevs/                  # adapter for PythonPDEVS minimal kernel
│   └── reference/                # hand-rolled flat-FEL engine (floor)
├── run_devstone.py               # pyjevsim-only runner
├── run_compare.py                # cross-engine comparison runner
└── results/
    ├── BASELINE.md               # captured baseline numbers
    ├── baseline.csv
    └── devstone_sweep.csv
```

### pyjevsim-only sweep

```
python -m benchmark.run_devstone --sweep \
    --output benchmark/results/devstone_sweep.csv
```

### Cross-engine comparison

```
pip install xdevs                                       # optional
python -m benchmark.run_compare --list-engines
python -m benchmark.run_compare \
    --output benchmark/results/baseline.csv
```

### Sparse-time baseline

`run_sparse` runs a tiny periodic-generator-plus-sink topology while
sweeping the inter-event simulated period. Holds the work constant at
100 events; only the simulated-time gap between events varies. Isolates
per-tick overhead in V_TIME mode (see
[`benchmark/results/SPARSE.md`](benchmark/results/SPARSE.md)):

```
python -m benchmark.run_sparse --output benchmark/results/sparse.csv
```

### Output aliasing test

`benchmark/aliasing_test.py` empirically demonstrates that all four
engines share output value references across multiple subscribers — see
[`benchmark/results/ALIASING.md`](benchmark/results/ALIASING.md). The
prevailing convention is "treat received values as immutable; copy on
the receiver if you need to mutate".

Current baseline (best-of-three, no synthetic CPU work) — see
[`benchmark/results/BASELINE.md`](benchmark/results/BASELINE.md):

| variant | d × w | pyjevsim tr/s | xdevs tr/s | pypdevs tr/s | reference tr/s |
|---------|-------|---------------|------------|--------------|----------------|
| LI      | 4 × 4 |  175 k        |  689 k     |  765 k       | 1.68 M         |
| HI      | 4 × 4 |  233 k        |  546 k     |  888 k       | 2.00 M         |
| HO      | 4 × 4 |  241 k        |  757 k     |  918 k       | 1.97 M         |

Use `--int-cycles N` / `--ext-cycles N` to inject synthetic CPU work per
transition and shift the measurement toward user-code cost.

## Debugging Uncaught Output Messages

By default `SysExecutor` drops output messages that hit a port with no
downstream coupling — the simulator stays on its fast path and the
events disappear silently. When wiring up a model graph it is often
useful to know *which* events are leaking; pass `track_uncaught=True`
and they get routed to the built-in `DefaultMessageCatcher` (accessible
as `se.dmc`) so you can observe them:

```python
se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, track_uncaught=True)
```

The flag costs ~10-15% throughput on dense graphs with many dangling
outputs (every uncoupled emit pays for one `ext_trans` + reschedule on
the catcher), so leave it off in production runs.

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

Runs one RTI-granted simulation step using the same Parallel-DEVS
four-phase tick that the standalone V_TIME path uses, so HLA federates
get correct `δ_int / δ_ext / δ_con` semantics:

- Every event whose `req_time <= granted_time` fires inside the call.
- Multiple cascade rounds at the same simulated instant complete in one
  `step()` (sigma=0 chains do not require multiple grants).
- During each round, `global_time` reflects the actual event time so
  models observe correct simulated time inside their transitions.
- Per IEEE 1516-2010, `global_time` lands at `granted_time` when the
  call returns, even if the last processed event was earlier.
- Returns the `output_event_queue` contents drained during this step
  (a `deque` of `(time, message)` tuples) so the federate can republish
  them as RTI interactions.

### `get_next_event_time()`

Returns the earliest scheduled event time across the FEL and the
external-event queue. Use it to compute the Time Advance Request value
for the RTI.

### Federate ambassador

pyjevsim ships the simulator-side hooks (above) but not an RTI
ambassador. Wire `step` / `get_next_event_time` /
`insert_external_event` / `set_output_event_callback` into the federate
ambassador of your chosen IEEE 1516-2010 RTI client.

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
