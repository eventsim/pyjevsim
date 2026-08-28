# pyjevsim HLA examples

This directory contains a local bound-port chat example and two legacy
integration examples for external RTI gateway projects. They share the
`Chatter` model in `_chat_model.py`; each runner supplies its own transport and
startup configuration.

| Demo                | RTI                      | Run with                                              |
|---------------------|--------------------------|-------------------------------------------------------|
| **`chat_loopback.py`** | none (in-process)     | `python -m examples.hla.chat_loopback`                |
| `chat_pitch/`       | Pitch pRTI               | `chat_pitch/run_demo.sh` (orchestrates 2 gateways + 2 federates) |
| `chat_gorti/`       | gorti rtid               | `chat_gorti/run_demo.sh` (orchestrates rtid + 2 federates) |

Start with `chat_loopback.py` to see binding-based send and receive in one
process without an RTI. For federation lifecycle, declarations, and grant
handling, use [`examples/hla_pingpong`](../hla_pingpong/).

| Directory      | RTI           | Transport implementation                       |
|----------------|---------------|------------------------------------------------|
| `chat_pitch/`  | Pitch pRTI    | `PitchTransport` → `kdx_rti.GatewayClient` (ZMQ → Java gateway → pRTI) |
| `chat_gorti/`  | gorti rtid    | `GortiTransport` → `rti1516e.Rti1516eAmbassador` (gRPC) |

## Pre-requisite layout

Each example imports the shared model via:

```python
from examples.hla._chat_model import Chatter
from examples.hla.chat_<name>.transport import <Name>Transport
```

The runner scripts insert the pyjevsim repo root onto `sys.path`, so
they work as `python -m examples.hla.chat_pitch.run alice` from the
repo root without `pip install`.

## What's NOT in these examples

- Object-instance lifecycle. Both transports handle interactions only and do
  not call `registerObjectInstance` or `discoverObjectInstance`.
- DDM regions, ownership management, save/restore, sync points.
- Reconnect after RTI failure.

The extension API is documented in
[`docs/hla/rti_interface.md`](../../docs/hla/rti_interface.md).

## Verifying without an RTI

`chat_loopback.py` is a two-model in-process demo using one
`pyjevsim.hla.LoopbackTransport` and one `SysExecutor`. It exercises bound
send and receive paths without federation lifecycle services or external
dependencies. Run it:

```sh
python -m examples.hla.chat_loopback                  # default 3 messages each
python -m examples.hla.chat_loopback --count 5 --period 0.5 --end 5
```

Expected output:

```
-- chat_loopback: each model sends 3, period=1.0s --
[alice] heard 'bob': hello from bob #1
[bob] heard 'alice': hello from alice #1
[alice] heard 'bob': hello from bob #2
...
-- done at t=3.0 --
```

The HLA factory regression tests exercise the same two model-bound senders
over the loopback transport.

## Automated demos with external RTIs

Each subdir has a `run_demo.sh` that brings up the RTI processes,
runs both federates in parallel, captures their logs, and prints the chat
output. Both scripts trap `EXIT/INT/TERM` and stop their child processes
during cleanup.

### Pitch (assumes pRTI CRC is already running):

```sh
COUNT=3 PERIOD=0.5 END=8 ./examples/hla/chat_pitch/run_demo.sh
```

Required env: `PRTI1516E_HOME` + `KDX_RTI_DIR` (defaults to a sibling
`kdx-rti` checkout).

### gorti (rtid is started by the script):

```sh
COUNT=3 PERIOD=0.5 END=8 ./examples/hla/chat_gorti/run_demo.sh
```

Required env: `RTID` (path to the `rtid` binary, defaults to
`<sibling-gorti>/rtid`) and the `rti1516e` Python package installed.

## Comparing application event traces

The deterministic chat example can produce a stable, application-level event
trace for each federate. Both `run_demo.sh` scripts omit wall-clock timestamps
and correlation identifiers and sort JSON payload keys. Comparing these files
can reveal differences in the lifecycle, data, or logical-time sequence seen
by the example.

This comparison covers only the recorded application events. It does not
compare RTI wire bytes or establish HLA conformance.

```sh
# 1. Run both demos with the SAME COUNT/PERIOD/END:
COUNT=5 PERIOD=1 END=10 ./examples/hla/chat_pitch/run_demo.sh
COUNT=5 PERIOD=1 END=10 ./examples/hla/chat_gorti/run_demo.sh

# 2. Diff the per-federate traces:
./examples/hla/diff_traces.sh
# → "PASS: gorti traces match Pitch traces for both federates." (rc=0)
# → or shows the diverging lines and exits non-zero
```

What gets traced (one event per line, fields are `key=value`):

```
JOIN federation=ChatFederation federate=alice fom=Chat-evolved.xml
PUBLISH kind=interaction fom=HLAinteractionRoot.Communication
SUBSCRIBE kind=interaction fom=HLAinteractionRoot.Communication
TAR target=1
GRANT granted=1
SEND kind=interaction fom=HLAinteractionRoot.Communication payload=[{"from":"alice","text":"hello from alice #1"}]
RECV kind=interaction fom=HLAinteractionRoot.Communication payload=[{"from":"bob","text":"hello from bob #1"}]
TAR target=2
GRANT granted=2
...
RESIGN
CLOSE
```

The tracing is implemented as `examples/hla/_trace.py::TracingTransport`
— a decorator that wraps any pyjevsim.hla.Transport. It logs every
call (lifecycle + data + time advance) to a sink file. Both runners
take a `--trace-file <path>` flag; the shell scripts pass it
automatically.

Logical-time request and grant values are included because they affect the
example's behavior. A difference between traces should be investigated as a
possible configuration, adapter, or application-behavior difference.

Wall-clock timestamps and correlation identifiers are omitted because they
naturally differ between runs.
