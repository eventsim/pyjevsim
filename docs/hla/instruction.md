# HLA developer guide

The guide has two paths:

1. **pyjevsim users** who want to turn an existing DEVS model into an
   HLA federate.
2. **Transport authors** who want to plug pyjevsim into a specific RTI
   binding.

The [HLA design reference](specification.md) describes the runtime data path,
and the [RTI backend interface](rti_interface.md) covers adapter development.

## 1. Mental model

```
Your code:    BehaviorModel  →  output() emits SysMessage on a port
                                ↓
              HLAExecutor       (intercepts ports declared in bindings)
                                ↓                      ↓
                         Transport.send(...)     msg_deliver  (local couplings)
```

The model class does not need to import the HLA package. A compatible model can
be used in:
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
# For a single-connector local test:
from pyjevsim.hla import LoopbackTransport
transport = LoopbackTransport()

# For multiple local federates, create one InProcessFederation and one
# InProcessRTI per federate. For a live run, select "pitch" or "portico",
# or the experimental source-installed "gorti" adapter, with create_rti(...).
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

The model class remains unchanged; the executor factory, bindings, transport,
and federation lifecycle provide the HLA configuration.

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

`object_class` is optional transport metadata. A custom transport may use it
to decide which object class to register. The built-in Pitch and Portico
adapters and the experimental GORTI adapter instead resolve the class from
their explicit FOM map; inbound bindings can therefore leave it unset. The
GORTI path does not expose complete Object Management or a public
multi-instance API.

## 4. Threading model

- The model's `output / int_trans / ext_trans / con_trans` are called
  on the `SysExecutor`'s simulation thread, exclusively.
- `Transport.on_receive(cb)` registers the receiver. A live backend may invoke
  that receiver from a backend-owned thread. pyjevsim moves the event into the
  simulation through the lock-protected `SysExecutor.insert_external_event`
  method.
- Model transitions still run on the simulation thread. Do not access model
  state directly from a custom transport callback; route inbound data through
  `_emit` and the executor.

## 5. Common pitfalls

1. **Bound `out` ports are RTI-only.** A `SysMessage` emitted on a bound
   `out` port goes to the transport and is **not** also delivered through
   local coupling. If you need both, declare two ports.
2. **Direction is enforced.** Sending through an `in` binding is ignored;
   inbound events have routes only for `in`/`inout` bindings. Calling
   `publish(in_binding)` or `subscribe(out_binding)` raises `ValueError`.
3. **`object_class` is optional.** Built-in live transports use the FOM map;
   custom transports may choose to require the binding hint themselves.
4. **HLA_TIME is logical-time only.** If you also want wallclock pacing,
   wrap your `run_until` loop with a sleep that matches your
   `time_resolution`. The framework will not do it for you.
5. **The grant increment must be positive.** The second argument to
   `Federate.run_until` is historically named `lookahead` and raises
   `ValueError` when non-positive. The backend owns the separate HLA regulating
   interval: Pitch uses its configured lookahead; Portico uses one internal
   RTI sub-step.

## 6. Implementing a backend

```python
from pyjevsim.hla import RTIConnector

class MyTransport(RTIConnector):
    def _do_send(self, binding, wire, timestamp):
        # Translate the encoded value to the RTI API.
        ...

    def _do_request_time_advance(self, target):
        # Wait for the RTI grant and return its logical time.
        ...

    # A receive callback forwards data with:
    # self._emit(kind, fom_id, wire, timestamp)
```

This is the minimum surface for local and test backends. A live adapter also
implements the lifecycle and declaration hooks it needs, owns object and class
handles, and calls `_emit` from its receive callback. See
[RTI backend interface](rti_interface.md) for the complete contract.

## 7. Where to look in the code

| Concept            | File                                |
|--------------------|-------------------------------------|
| Bindings           | `pyjevsim/hla/bindings.py`          |
| Transport contract | `pyjevsim/hla/transport.py`         |
| Output interception| `pyjevsim/hla/hla_executor.py`      |
| Factory            | `pyjevsim/hla/factory.py`           |
| Lifecycle + loop   | `pyjevsim/hla/federate.py`          |
| Time grant tick    | `pyjevsim/system_executor.py` (`step`) |
| External events    | `pyjevsim/system_executor.py` (`insert_external_event`) |
