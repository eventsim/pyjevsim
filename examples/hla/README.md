# pyjevsim HLA examples

Two transport-specific chat-federate examples sharing one `Chatter`
BehaviorModel (`_chat_model.py`). Same model class runs against both
RTIs — only the `Transport` and the bring-up script differ.

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

The shared model has no HLA imports, so it can be exercised with
`pyjevsim.hla.LoopbackTransport` for a self-contained two-federate
demo without any external RTI:

```python
from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla import (
    Federate, HLAExecutorFactory, HLAInteraction, LoopbackTransport,
)
from examples.hla._chat_model import Chatter

tx = LoopbackTransport()
sys_exec = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
chat = HLAInteraction("Communication", direction="inout")
sys_exec.exec_factory = HLAExecutorFactory(tx, {
    "alice": {Chatter.OUTBOX: HLAInteraction("Communication", direction="out"),
              Chatter.INBOX:  HLAInteraction("Communication", direction="in")},
    "bob":   {Chatter.OUTBOX: HLAInteraction("Communication", direction="out"),
              Chatter.INBOX:  HLAInteraction("Communication", direction="in")},
})
sys_exec.register_entity(Chatter("alice"))
sys_exec.register_entity(Chatter("bob"))

# Drive without a Federate (LoopbackTransport doesn't need lifecycle).
for _ in range(10):
    sys_exec.step(sys_exec.global_time + 1.0)
```

This is what `tests/hla/test_m2_factory.py::test_M2_6` exercises —
the test itself is a working two-federate demo.
