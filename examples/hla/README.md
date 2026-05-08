# pyjevsim HLA examples

Two transport-specific chat-federate examples sharing one `Chatter`
BehaviorModel (`_chat_model.py`). Same model class runs against both
RTIs — only the `Transport` and the bring-up script differ.

| Demo                | RTI                      | Run with                                              |
|---------------------|--------------------------|-------------------------------------------------------|
| **`chat_loopback.py`** | none (in-process)     | `python -m examples.hla.chat_loopback`                |
| `chat_pitch/`       | Pitch pRTI               | `chat_pitch/run_demo.sh` (orchestrates 2 gateways + 2 federates) |
| `chat_gorti/`       | gorti rtid               | `chat_gorti/run_demo.sh` (orchestrates rtid + 2 federates) |

**Start with `chat_loopback.py`** — no external RTI required, runs in
one process, demonstrates the full subsystem in ~30 seconds.

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

- Object-instance lifecycle. Both transports handle interactions
  only. A production transport would track object handles via
  `registerObjectInstance` / `discoverObjectInstance`.
- DDM regions, ownership management, save/restore, sync points.
- Reconnect after RTI failure.

For production use, extend the transport in `transport.py` (or
upstream a richer one to the kdx-rti / gorti repo).

## Verifying without an RTI

`chat_loopback.py` is a complete in-process two-federate demo using
`pyjevsim.hla.LoopbackTransport`. No external dependencies. Run it:

```sh
python -m examples.hla.chat_loopback                  # default 3 messages each
python -m examples.hla.chat_loopback --count 5 --period 0.5 --end 5
```

Expected output:

```
-- chat_loopback: each federate sends 3, period=1.0s --
[alice] heard 'bob': hello from bob #1
[bob] heard 'alice': hello from alice #1
[alice] heard 'bob': hello from bob #2
...
-- done at t=3.0 --
```

`tests/hla/test_m2_factory.py::test_M2_6` is the same demo expressed
as a regression test.

## Automated demos with real RTIs

Each subdir has a `run_demo.sh` that brings up the RTI processes,
runs both federates in parallel, captures their logs, prints the
chat output, and tears everything down on exit. Both scripts trap
`EXIT/INT/TERM` to ensure no orphaned processes survive.

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

## Cross-RTI conformance comparison

The chat federate is deterministic, so its event sequence under two
semantically-identical RTIs should be byte-identical. Both
`run_demo.sh` scripts emit per-federate **event traces** in a stable
canonical format (no wallclock timestamps, no correlation IDs, sorted-
key JSON payloads) — `diff` between Pitch and gorti traces reveals
any semantics divergence.

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

**Logical time values (TAR target, GRANT granted) are included on
purpose** — they're part of the HLA semantics under test. If gorti
grants different times than Pitch under the same time-management
configuration, that's a real bug worth catching.

**Wallclock timestamps and correlation IDs are stripped** — those
naturally differ between runs and would create false-positive diffs.
