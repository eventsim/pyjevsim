# pyjevsim

[![PyPI](https://img.shields.io/pypi/v/pyjevsim.svg)](https://pypi.org/project/pyjevsim/)
[![Python](https://img.shields.io/pypi/pyversions/pyjevsim.svg)](https://pypi.org/project/pyjevsim/)
[![Docs](https://readthedocs.org/projects/pyjevsim/badge/?version=latest)](https://pyjevsim.readthedocs.io/en/latest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Introduction

pyjevsim is a DEVS (discrete event system specification) modeling and
simulation environment with built-in journaling. It supports snapshot
and restore of individual models or the full simulation engine,
virtual-time and real-time execution, and HLA (IEEE 1516-2010) federate
integration with pluggable RTI backends (including Pitch pRTI).
Compatible with Python 3.10+.

Full documentation: <https://pyjevsim.readthedocs.io/en/latest/>

### What's new in 2.1

- **Pluggable RTI backends.** A new `RTIConnector` interface
  (`pyjevsim.hla`) lets any RTI drive a pyjevsim federate without
  touching model code. A backend implements just two methods; direction
  enforcement, FOM codec, callback dispatch and the join/resign state
  machine are inherited. Ships an in-process bus (`inprocess`) for
  multi-federate testing and a **Pitch pRTI** (IEEE 1516-2010) backend
  (`pitch`, via JPype). Pick one by name with `create_rti(...)`.
- **HLA ping-pong example** ([`examples/hla_pingpong/`](examples/hla_pingpong/)):
  two federates (ping/pong) exchanging interactions and synchronizing an
  object attribute — runnable offline (no Java) or against a live RTI.
  Verified live against Pitch pRTI Free 5.5.2.
- **Unified DEVS tick.** V_TIME, R_TIME and HLA_TIME now share one
  two-phase tick body, so external events get correct confluent
  (`con_trans`) semantics on every execution path.

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

From PyPI (recommended):

```
pip install pyjevsim
```

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
pip install pyjevsim[dev]
```

The Pitch pRTI backend needs JPype, declared under the `hla-pitch` extra
(the `loopback` / `inprocess` backends need nothing beyond the core):

```
pip install pyjevsim[hla-pitch]
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
    def time_advance(self):
        return 1


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
    def time_advance(self):
        return Infinite


se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
gen = Gen("g")
sink = Sink("s")
se.register_entity(gen)
se.register_entity(sink)
se.coupling_relation(gen, "out", sink, "in")
se.simulate(5)
```

See the [quick-start guide](https://pyjevsim.readthedocs.io/en/latest/pyjevsim_quick_start.html)
for structural models, snapshots, and HLA stepped execution.

### Examples

The [`examples/`](examples/) directory contains:

- **`banksim/`** — bank queue simulation demonstrating BehaviorModel,
  StructuralModel, and snapshot/restore.
- **`atsim/`** — anti-torpedo simulator with self-propelled and
  stationary decoy models.
- **`mwmsim/`** — municipal waste management agent-based model.
- **`hla_pingpong/`** — two HLA federates (ping/pong) demonstrating
  federation join/resign, interaction exchange, and object-attribute
  synchronization. Run offline (`run_inprocess.py`, no Java) or against a
  live Pitch pRTI (`run_pitch.py`).

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

## HLA/RTI Integration

pyjevsim integrates with HLA (IEEE 1516-2010) at two levels: a high-level
**pluggable RTI backend** layer (`pyjevsim.hla`) that runs ordinary DEVS
models as federates, and the low-level `HLA_TIME` stepping hooks for
custom federate ambassadors.

### Pluggable RTI backends (`pyjevsim.hla`)

Your `BehaviorModel` declares HLA *bindings* on its ports (an
`HLAInteraction` or `HLAAttribute` per FOM id); an `HLAExecutorFactory`
bridges those ports to a transport; and a `Federate` drives the
time-advance loop. The transport is chosen by name — the same models run
on any backend:

```python
from pyjevsim import SysExecutor, ExecutionType
from pyjevsim.hla import (
    create_rti, available_rtis, HLAExecutorFactory, HLAInteraction, Federate,
)

print(available_rtis())            # ['inprocess', 'loopback', 'pitch']

transport = create_rti("inprocess")            # or "pitch" for live Pitch pRTI
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

Built-in backends:

| Name | Use | Dependency |
|------|-----|------------|
| `loopback` | self-mirror, single-federate unit tests | none |
| `inprocess` | multi-federate in-process bus (tests/demos) | none |
| `pitch` | **Pitch pRTI** IEEE 1516-2010, live federation | `pip install pyjevsim[hla-pitch]` + Java ≥ 9 + a running CRC |

**Adding your own RTI** (CERTI, Portico, OpenRTI, MÄK, …): subclass
`RTIConnector` and implement `_do_send` + `_do_request_time_advance`
(plus optional lifecycle hooks), then `register_rti("name", factory)`.
See [`docs/hla/rti_interface.md`](docs/hla/rti_interface.md) for the full
guide and [`examples/hla_pingpong/`](examples/hla_pingpong/) for a
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

pyjevsim ships a ready-made Pitch pRTI backend (above) and an
`RTIConnector` interface for adding others. If instead you want to embed
the simulator into an existing federate ambassador, wire `step` /
`get_next_event_time` / `insert_external_event` /
`set_output_event_callback` into the ambassador of your chosen IEEE
1516-2010 RTI client directly — this is exactly what the `pitch` backend
does internally.

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
