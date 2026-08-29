# pyjevsim

[![PyPI](https://img.shields.io/pypi/v/pyjevsim.svg)](https://pypi.org/project/pyjevsim/)
[![Python](https://img.shields.io/pypi/pyversions/pyjevsim.svg)](https://pypi.org/project/pyjevsim/)
[![Docs](https://readthedocs.org/projects/pyjevsim/badge/?version=latest)](https://pyjevsim.readthedocs.io/en/latest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/eventsim/pyjevsim/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21002028.svg)](https://doi.org/10.5281/zenodo.21002028)

## Introduction

pyjevsim is a DEVS (discrete event system specification) modeling and
simulation environment with built-in journaling. It supports snapshot
and restore of individual models or the full simulation engine,
virtual-time and real-time execution, and HLA (IEEE 1516-2010) federate
integration with pluggable RTI backends. Version 2.2.0 includes adapters for
Pitch pRTI and the open-source Portico RTI, plus an experimental native-Python
GORTI adapter.
Compatible with Python 3.10+.

Full documentation: <https://pyjevsim.readthedocs.io/en/latest/>

### Changes in 2.2

- **Portico backend.** The live HLA adapter now supports Portico 2.1.4 in
  addition to Pitch pRTI. Portico-specific handling covers its
  `HLAunicodeString` representation and receive-order reflection behavior.
- **Experimental GORTI backend.** A native-Python adapter supports selected
  interaction, object-attribute, and regulating/constrained logical-time paths
  through GORTI's source-installed `rti1516e` SDK and a separately built
  `rtid`, without Java or JPype.
- **AT/SIM reference data.** The two-federate AT/SIM example includes two
  30-tick scenarios, complete 180-row reference trajectories, and commands
  for offline and optional live-RTI comparison.
- **Documented service scope.** The HLA guide now includes architecture and
  sequence diagrams, the implemented IEEE 1516 service subset, logical-time
  behavior, backend extension guidance, related projects, and known
  limitations.
- **Direction checks and failure reporting.** Binding directions are checked at
  runtime, Portico examples use a bundled same-JVM configuration, and live
  AT/SIM runs report missing peer data or worker failures.

### What's new in 2.1

- **Pluggable RTI backends.** A new `RTIConnector` interface
  (`pyjevsim.hla`) defines the extension boundary through which an RTI can
  drive a pyjevsim federate without embedding RTI calls in model code. A
  minimal backend implements two abstract methods; a live HLA adapter also
  supplies lifecycle/declaration and inbound callback hooks. Direction
  enforcement, FOM codec, callback dispatch and the join/resign state
  machine are inherited. Ships an in-process bus (`inprocess`) for
  multi-federate testing and a **Pitch pRTI** (IEEE 1516-2010) backend
  (`pitch`, via JPype). Pick one by name with `create_rti(...)`.
- **HLA ping-pong example** ([`examples/hla_pingpong/`](https://github.com/eventsim/pyjevsim/tree/main/examples/hla_pingpong)):
  two federates (ping/pong) exchanging interactions and synchronizing an
  object attribute — runnable offline (no Java) or against a live RTI.
  Verified live against Pitch pRTI Free 5.5.2.
- **Unified DEVS tick.** V_TIME, R_TIME and HLA_TIME now share one
  two-phase tick body. An imminent model with input at the same simulated
  instant uses `con_trans` in each mode.

### What's new in 2.0

- **Two-phase tick.** `SysExecutor` evaluates every imminent model's
  `output()` first, then routes outputs and applies transitions —
  fixing confluent-event ordering under Parallel-DEVS semantics.
- **HLA stepped execution.** `step(granted_time)` and
  `get_next_event_time()` let an IEEE 1516-2010 RTI federate drive
  pyjevsim without owning the main loop.
- **V_TIME jump-to-next-event.** The virtual-time scheduler hops
  directly to the next scheduled event instead of advancing by a fixed
  `time_resolution`, eliminating idle ticks on sparse models.
- **Opt-in uncaught-message tracking** for debugging dangling outputs.
- **DEVStone benchmark suite** with cross-engine comparison adapters.

## Installing

From PyPI:

```
pip install pyjevsim
```

This installs the latest published release. Use the source checkout below to
test changes that have not yet been tagged.

From source:

```
git clone https://github.com/eventsim/pyjevsim
cd pyjevsim
pip install -e .
```

## Dependencies

- Python >= 3.10
- `dill >= 0.3.6` (installed automatically) — used for model
  serialization and restoration.

`pytest` is required only to run the test suite and is declared under
the `dev` extra:

```
python -m pip install "pyjevsim[dev]"
```

The Java-backed Pitch and Portico adapters need JPype, declared under the
`hla-java` extra (the older `hla-pitch` name remains as a compatible alias).
The `loopback` and `inprocess` backends need nothing beyond the core package:

```
python -m pip install "pyjevsim[hla-java]"
```

The experimental GORTI backend is not installed by a pyjevsim extra because
GORTI's Python SDK is not currently published on PyPI. Install the SDK from a
GORTI source checkout before selecting the `gorti` backend:

```powershell
python -m pip install -e C:\path\to\gorti\pysdk
```

## Quick Start

A minimal generator → sink simulation:

```python
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class Gen(BehaviorModel):
    def __init__(self, name):
        super().__init__(name)
        self.init_state("Generate")
        self.insert_state("Generate", 1)
        self.insert_output_port("out")

    def ext_trans(self, port, msg): pass
    def int_trans(self): pass
    def output(self, md):
        msg = SysMessage(self.get_name(), "out")
        msg.insert("tick")
        md.insert_message(msg)
class Sink(BehaviorModel):
    def __init__(self, name):
        super().__init__(name)
        self.init_state("Idle")
        self.insert_state("Idle", Infinite)
        self.insert_input_port("in")

    def ext_trans(self, port, msg):
        print(f"received: {msg.retrieve()}")
    def int_trans(self): pass
    def output(self, md): pass
se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
gen = Gen("g")
sink = Sink("s")
se.register_entity(gen)
se.register_entity(sink)
se.coupling_relation(gen, "out", sink, "in")
se.simulate(5)
```

The duration passed to `insert_state()` is the time advance for that state;
the executor does not call a model-defined `time_advance()` method.

See the [quick-start guide](https://pyjevsim.readthedocs.io/en/latest/pyjevsim_quick_start.html)
for structural models, snapshots, and HLA stepped execution.

### Examples

The [`examples/`](https://github.com/eventsim/pyjevsim/tree/main/examples) directory contains:

- **`banksim/`** — bank queue simulation demonstrating BehaviorModel,
  StructuralModel, and snapshot/restore.
- **`atsim/`** — anti-torpedo simulator with self-propelled and
  stationary decoy models.
- **`mwmsim/`** — municipal waste management agent-based model.
- **`hla_pingpong/`** — two HLA federates (ping/pong) demonstrating
  federation join/resign, interaction exchange, and object-attribute
  synchronization. Run offline (`run_inprocess.py`, no Java) or against a
  live Pitch pRTI (`run_pitch.py`).
- **`hla_atsim/`** — the `atsim` anti-torpedo scenario split into two HLA
  federates (surfaceship + torpedo) exchanging positions as HLA object
  attributes. Its sorted, formatted application-state rows exactly reproduce
  a committed single-executor reference for both decoy scenarios; the
  offline comparison needs no Java or proprietary RTI (`verify_equivalence.py`).

### Output messages are shared by reference

When a model's output port has multiple downstream subscribers, every
subscriber receives the **same** `SysMessage` object. pyjevsim does not
deep-copy outputs during propagation. Treat received messages as immutable;
if a model needs to change a payload, copy it on the receiver side. The
comparison in `benchmark/aliasing_test.py` illustrates this behavior.

```python
def ext_trans(self, port, msg):
    payload = list(msg.retrieve())   # local copy, safe to mutate
    payload.append(my_local_data)
    ...
```

See [`benchmark/results/ALIASING.md`](https://github.com/eventsim/pyjevsim/blob/main/benchmark/results/ALIASING.md) for
the test scope and usage notes.

## Benchmarks

The [`benchmark/`](https://github.com/eventsim/pyjevsim/tree/main/benchmark) directory contains a DEVStone suite plus
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
    ├── baseline.csv               # generated output, gitignored
    └── devstone_sweep.csv         # generated output, gitignored
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
[`benchmark/results/SPARSE.md`](https://github.com/eventsim/pyjevsim/blob/main/benchmark/results/SPARSE.md)):

```
python -m benchmark.run_sparse --output benchmark/results/sparse.csv
```

### Output aliasing test

`benchmark/aliasing_test.py` checks whether multiple subscribers receive the
same output value object. pyjevsim shares that value by reference. The script
also contains optional xdevs, PythonPDEVS, and reference-engine adapters;
details are in
[`benchmark/results/ALIASING.md`](https://github.com/eventsim/pyjevsim/blob/main/benchmark/results/ALIASING.md).
Treat a received value as immutable, or copy it before changing it.

The [historical cross-engine record](https://github.com/eventsim/pyjevsim/blob/main/benchmark/results/BASELINE.md) contains
one capture from 2026-05-05 and its limitations. Run the command above to
measure the current commit and retain its generated CSV with the environment
details.

Use `--int-cycles N` / `--ext-cycles N` to inject synthetic CPU work per
transition and shift the measurement toward user-code cost.

## Debugging Uncaught Output Messages

By default, `SysExecutor` drops a message emitted on a port with no downstream
coupling. Pass `track_uncaught=True` to route those messages to the built-in
`DefaultMessageCatcher`, available as `se.dmc`:

```python
se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, track_uncaught=True)
```

Each captured message invokes the catcher's `ext_trans` and reschedules it, so
this diagnostic mode adds work for every uncoupled output. Enable it only when
that information is needed.

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

`SysExecutor` protects its pause state and external-event queue with a
condition lock. Model transitions still run on the simulation thread.

### Pause / Resume

`pause_sim()` stops the simulation loop; external threads may continue to add
events. `resume_sim()` wakes the paused loop.

```python
se.pause_sim()    # Pauses the simulation loop
# External threads can safely call insert_external_event() while paused
se.resume_sim()   # Resumes the simulation loop
```

### External Event Injection

`insert_external_event()` adds an event to the protected input queue. The
scheduled time is relative to the executor's current `global_time`.

```python
se.insert_external_event("port_name", message, scheduled_time=0)
```

### Output Event Callback

`set_output_event_callback()` registers a no-argument callback that runs when
an external output event is queued. `handle_external_output_event()` returns
a copied snapshot and clears the queue under the same lock.

```python
se.set_output_event_callback(lambda: print("output ready"))
events = se.handle_external_output_event()
```

## HLA/RTI Integration

pyjevsim integrates with HLA (IEEE 1516-2010) at two levels: a high-level
**pluggable RTI backend** layer (`pyjevsim.hla`) that runs ordinary DEVS
models as federates, and the low-level `HLA_TIME` stepping hooks for
custom federate ambassadors.

The repository's [HLA validation and reproducibility guide](https://github.com/eventsim/pyjevsim/blob/main/docs/hla-validation/README.md)
collects the architecture diagrams, exact equivalence criterion, full expected
traces, RTI/service coverage, limitations, and related projects.

### Pluggable RTI backends (`pyjevsim.hla`)

Your `BehaviorModel` declares HLA *bindings* on its ports (an
`HLAInteraction` or `HLAAttribute` per FOM id); an `HLAExecutorFactory`
bridges those ports to a transport; and a `Federate` drives the
time-advance loop. The transport is chosen by name — the same models run
on the shipped backends when their FOM and required service subset are
supported:

```python
from pyjevsim import SysExecutor, ExecutionType
from pyjevsim.hla import (
    create_rti, available_rtis, HLAExecutorFactory, HLAInteraction, Federate,
)

print(available_rtis())     # ['gorti', 'inprocess', 'loopback', 'pitch', 'portico']

transport = create_rti("inprocess")   # or "pitch" / "portico" / "gorti"
sys_exec = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
sys_exec.exec_factory = HLAExecutorFactory(
    transport, {"chatter": {"out": HLAInteraction("Comm.Msg", direction="out")}}
)
sys_exec.register_entity(my_model)

fed = Federate(sys_exec, transport)
fed.join("MyFederation", "chatter", fom_paths=["Comm.xml"])
fed.publish(HLAInteraction("Comm.Msg", direction="out"))
fed.run_until(end_time=60.0, lookahead=1.0)
fed.resign()
```

The `run_until` argument historically named `lookahead` is the grant-request
increment. The backend owns the distinct HLA regulating interval and time-unit
mapping: Pitch uses its configured interval; Portico uses one internal RTI
sub-step; GORTI maps pyjevsim logical time directly to RTI logical time.

Built-in backends:

| Name | Use | Dependency |
|------|-----|------------|
| `loopback` | self-mirror, single-federate unit tests | none |
| `inprocess` | multi-federate in-process bus (tests/demos) | none |
| `pitch` | **Pitch pRTI** IEEE 1516-2010, live federation | `python -m pip install "pyjevsim[hla-java]"` + Java ≥ 11 + a running CRC |
| `portico` | **Portico** (open source) IEEE 1516-2010, live federation | `python -m pip install "pyjevsim[hla-java]"` + Java ≥ 11 + `portico.jar` (no CRC) |
| `gorti` | experimental **GORTI** native-Python client for selected interaction, object-attribute, and logical-time paths | source-install the SDK with `python -m pip install -e C:\path\to\gorti\pysdk` + a reachable `rtid` |

The Java-backed live backends program against the standard `hla.rti1516e`
API; the
`portico` backend subclasses the `pitch` implementation and adapts its
`HLAunicodeString` codec and receive-order delivery of time-stamped
reflections. See
[`pyjevsim/hla/backends/portico.py`](https://github.com/eventsim/pyjevsim/blob/main/pyjevsim/hla/backends/portico.py).
The `gorti` backend uses GORTI's `rti1516e` Python SDK directly and supports
interactions, object attributes, and regulating/constrained logical time
without a JVM.

Recorded GORTI functional checks cover interaction exchange, object instance
registration/discovery, attribute update/reflection, and logical-time grants.
They do not establish release-grade GORTI support, a public multi-instance or
explicit delete-object API, complete HLA Object Management, or formal IEEE
1516 conformance.

**Adding your own RTI** (CERTI, OpenRTI, MÄK, …): subclass
`RTIConnector` and implement `_do_send` + `_do_request_time_advance`
(the minimal abstract surface). A live HLA adapter also overrides join,
declaration, cleanup, and invokes `_emit` from its receive callback. Then call
`register_rti("name", factory)`.
See [`docs/hla/rti_interface.md`](https://github.com/eventsim/pyjevsim/blob/main/docs/hla/rti_interface.md) for the full
guide and [`examples/hla_pingpong/`](https://github.com/eventsim/pyjevsim/tree/main/examples/hla_pingpong) for a
working two-federate example.

### Low-level stepping (`HLA_TIME` mode)

If you prefer to wire pyjevsim into your own federate ambassador, use
`HLA_TIME` mode directly with `step()` and `get_next_event_time()`.

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

Runs one RTI-granted simulation step using the same two-phase Parallel-DEVS
tick as the standalone V_TIME path:

- Every event whose `req_time <= granted_time` fires inside the call.
- Multiple cascade rounds at the same simulated instant complete in one
  `step()` (sigma=0 chains do not require multiple grants).
- During each round, `global_time` is the event time read by model
  transitions.
- After processing, pyjevsim sets `global_time` to `granted_time`, even if the
  last processed event was earlier.
- Returns the `output_event_queue` contents drained during this step
  (a `deque` of `(time, message)` tuples) so the federate can republish
  them as RTI interactions.

### `get_next_event_time()`

Returns the earliest scheduled event time across the FEL and the
external-event queue. Use it to compute the Time Advance Request value
for the RTI.

### Federate ambassador

pyjevsim ships ready-made Pitch pRTI and Portico backends, the experimental
GORTI adapter described above, and an
`RTIConnector` interface for adding others. If instead you want to embed
the simulator into an existing federate ambassador, wire `step` /
`get_next_event_time` / `insert_external_event` /
`set_output_event_callback` into the ambassador of your chosen IEEE
1516-2010 RTI client directly — this is the core path used by `pitch` and its
`portico` subclass.

## Graceful Termination

```python
se.terminate_simulation()  # Sets SIMULATION_TERMINATED state
se.is_terminated()         # Returns True if terminated
```

Signal handlers (SIGTERM, SIGINT) automatically invoke `terminate_simulation()` on all registered SysExecutor instances.

## Support and contributing

Use [GitHub Issues](https://github.com/eventsim/pyjevsim/issues) for bug
reports, feature requests, and usage questions. See
[CONTRIBUTING.md](https://github.com/eventsim/pyjevsim/blob/main/CONTRIBUTING.md) for the development setup, test commands,
and pull-request guidelines. Security reports should follow
[SECURITY.md](https://github.com/eventsim/pyjevsim/blob/main/SECURITY.md).

## License   
Author: Changbeom Choi (@cbchoi)   
Copyright (c) 2014-2020 Handong Global University      
Copyright (c) 2021-2026 Hanbat National University    
License: MIT.  The full license text is available at:   
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE   
