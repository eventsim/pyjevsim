# pyjevsim HLA Subsystem — Developer Guide

This guide is for two audiences:
1. **pyjevsim users** who want to turn an existing DEVS model into an
   HLA federate.
2. **Transport authors** who want to plug pyjevsim into a specific RTI
   binding (gorti gRPC, kdx-rti ZMQ, native Pitch HLA, ...).

If you want to *implement* the subsystem itself, read
`docs/hla/specification.md` and `docs/hla/qa.md` instead.

## 1. Mental model

```
Your code:    BehaviorModel  →  output() emits SysMessage on a port
                                ↓
              HLAExecutor       (intercepts ports declared in bindings)
                                ↓                      ↓
                         Transport.send(...)     msg_deliver  (local couplings)
```

The model class never imports anything HLA. Same model runs in:
- pure DEVS unit tests (no transport),
- pyjevsim simulations with V_TIME or R_TIME,
- HLA federations under HLA_TIME.

What changes is the **factory** used to wrap the model and the
**execution mode** of `SysExecutor`.

## 2. Turning a model into a federate (5 steps)

### Step 1 — write your model in pure DEVS

```python
from pyjevsim import BehaviorModel, SysMessage

class Chatter(BehaviorModel):
    def __init__(self, name, period=1.0):
        super().__init__(name)
        self.insert_state("idle", period)
        self.init_state("idle")
        self.insert_input_port("inbox")
        self.insert_output_port("outbox")
        self._counter = 0

    def ext_trans(self, port, msg):
        if port == "inbox":
            payload = msg.retrieve()[0]
            print(f"[{self.get_name()}] heard: {payload}")

    def int_trans(self):
        self._counter += 1

    def output(self, deliver):
        m = SysMessage(self.get_name(), "outbox")
        m.insert({"text": f"hello #{self._counter}"})
        deliver.insert_message(m)
```

No HLA awareness. `outbox` and `inbox` are just port names.

### Step 2 — declare bindings

```python
from pyjevsim.hla import HLAInteraction

bindings_alice = {
    "outbox": HLAInteraction("Communication.ChatMsg", direction="out"),
    "inbox":  HLAInteraction("Communication.ChatMsg", direction="in"),
}
```

The keys are **port names on the model**. The values say "this port is
an HLA endpoint with this FOM identifier."

### Step 3 — pick a transport

```python
# In tests / for a self-contained two-federate demo:
from pyjevsim.hla import LoopbackTransport
transport = LoopbackTransport()

# In production:
# from kdx_rti.transport import KdxRtiTransport
# transport = KdxRtiTransport(endpoints=...)
#
# from gorti.transport import GortiTransport
# transport = GortiTransport(host=..., port=...)
```

### Step 4 — build the SysExecutor with the HLA factory

```python
from pyjevsim import SysExecutor, ExecutionType
from pyjevsim.hla import HLAExecutorFactory

sys_exec = SysExecutor(
    _time_resolution=1,
    _sim_name="alice-sim",
    ex_mode=ExecutionType.HLA_TIME,
)
sys_exec.exec_factory = HLAExecutorFactory(
    transport=transport,
    bindings_by_model={"alice": bindings_alice},
)
sys_exec.register_entity(Chatter("alice"))
```

That is the entire HLA-specific bring-up. The model class did not change.

### Step 5 — drive the federate

```python
from pyjevsim.hla import Federate

fed = Federate(sys_exec, transport)
fed.join("CommunicationFederation", "alice", fom_paths=["Communication.xml"])
fed.publish(bindings_alice["outbox"])
fed.subscribe(bindings_alice["inbox"])

fed.run_until(end_time=60.0, lookahead=1.0)

fed.resign()
transport.close()
```

`run_until` performs the tick / grant / step loop:

```
loop:
  target  = min(global_time + lookahead, end_time)
  granted = transport.request_time_advance(target)   # blocks on RTI
  sys_exec.step(granted)                              # processes events ≤ granted
  if global_time >= end_time: break
```

## 3. Working with attributes (object instances)

```python
from pyjevsim.hla import HLAAttribute

bindings_vehicle = {
    "position_out": HLAAttribute(
        "Vehicle.position", direction="out", object_class="Vehicle"
    ),
    "position_in": HLAAttribute(
        "Vehicle.position", direction="in"   # object_class resolved by transport
    ),
}
```

`object_class` is **required** for outbound updates because the
transport needs to know which object class to register the instance
under. For inbound reflects, the transport receives the class on the
wire and the binding does not need to repeat it.

## 4. Threading model

- The model's `output / int_trans / ext_trans / con_trans` are called
  on the `SysExecutor`'s simulation thread, exclusively.
- `Transport.on_receive(cb)` is invoked on a transport-owned thread.
  pyjevsim ships the event into the simulation via
  `SysExecutor.insert_external_event`, which is already lock-protected
  (`pyjevsim/system_executor.py:833`).
- You **do not** need to add locks in your model.

## 5. Important rules (the things that bite people)

1. **Bound `out` ports are RTI-only.** A `SysMessage` emitted on a bound
   `out` port goes to the transport and is **not** also delivered through
   local coupling. If you need both, declare two ports.
2. **Direction is enforced.** Sending on a port whose binding is
   `direction="in"` is a programming error (the message will be dropped
   with a warning). Conversely, transport-delivered events for a binding
   marked `direction="out"` are dropped.
3. **`object_class` is required for outbound `HLAAttribute`.** Caught at
   construction time — no silent failure.
4. **HLA_TIME is logical-time only.** If you also want wallclock pacing,
   wrap your `run_until` loop with a sleep that matches your
   `time_resolution`. The framework will not do it for you.
5. **`lookahead > 0` always.** RTI semantics. `Federate.run_until`
   raises `ValueError` if you forget.

## 6. Implementing a `Transport`

```python
from pyjevsim.hla import Transport, HLAInteraction, HLAAttribute

class MyTransport:
    def __init__(self):
        self._cb = None

    def send(self, binding, payload):
        # Translate (binding, payload) to your wire format and ship it.
        # binding.kind is "interaction" or "attribute".
        # binding.fom_id is the FOM-side identifier.
        ...

    def on_receive(self, callback):
        self._cb = callback

    def request_time_advance(self, target):
        # Block until your RTI grants. Return the granted time.
        ...

    def close(self):
        ...

    # Internal: when a message arrives from the RTI, do:
    #     self._cb(kind, fom_id, payload, timestamp)
```

The four methods above are the entire contract. Anything else (object
instance handles, region descriptors, save/restore) is your transport's
internal concern.

## 7. Migrating from kdx-rti's `HLAAdapter`

If you have a federate built on `kdx_rti.adapter.HLAAdapter`:

| Old (`HLAAdapter`)                                | New (`HLAExecutor`)                            |
|---------------------------------------------------|------------------------------------------------|
| User model couples to ~30 lifecycle ports         | Lifecycle moves to `Federate.{join,publish,...}` |
| User model couples to `reflect / interaction`     | Bindings on the receiving model's input ports  |
| User model emits to `updateAttributeValues`       | Bindings on the sending model's output ports   |
| `HLAAdapter` runs `Idle / Draining / Ticking`     | Gone — `Federate.run_until` drives `step()`    |
| `_kdx_rti_wake` private port                      | Gone — `HLAExecutor` calls `insert_external_event` directly |
| ZMQ I/O configured on adapter                     | Constructed and passed to `HLAExecutorFactory` |

The `HLAAdapter` becomes a `Transport` implementation: keep its three
ZMQ sockets, drop everything model-related.

## 8. Where to look in the code

| Concept            | File                                |
|--------------------|-------------------------------------|
| Bindings           | `pyjevsim/hla/bindings.py`          |
| Transport contract | `pyjevsim/hla/transport.py`         |
| Output interception| `pyjevsim/hla/hla_executor.py`      |
| Factory            | `pyjevsim/hla/factory.py`           |
| Lifecycle + loop   | `pyjevsim/hla/federate.py`          |
| Time grant tick    | `pyjevsim/system_executor.py:684`  (`step`) |
| External events    | `pyjevsim/system_executor.py:820` (`insert_external_event`) |
