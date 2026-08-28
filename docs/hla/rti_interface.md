# RTI backend interface

The adapter interface below is the extension point for new RTI backends. The
repository includes tested Pitch pRTI and Portico adapters. CERTI, OpenRTI,
MÄK, and custom surrogates are not shipped implementations.

The [HLA design reference](specification.md) describes how this interface fits
the executor and federate runtime.

## 1. Layering

```
 BehaviorModel (pure DEVS, no HLA imports)
      │  output() / ext_trans() on named ports
      ▼
 HLAExecutor ── intercepts bound ports ──► RTIConnector.send(binding, payload, timestamp)
      ▲                                          │  _codec.encode → _do_send  (RTI wire)
      │  parent.insert_external_event            ▼
 _HLARouter ◄── _emit(kind, fom_id, wire, ts) ── backend RX thread
      │           _codec.decode
      ▼
 SysExecutor.step(granted)  ◄── Federate.run_until ──► RTIConnector.request_time_advance(target)
```

The backend boundary has four parts:

| Piece | Type | Replace to… |
|-------|------|-------------|
| `RTIConnector` | nominal base class (ABC) | support a different RTI |
| `Codec`        | structural protocol      | map to a different FOM / encoding |
| `RTICapabilities` | dataclass            | advertise what a backend can do |
| registry       | name → factory           | select a backend by config string |

## 2. `RTIConnector` — the extension point

A backend subclasses `RTIConnector`. Two methods form the minimum abstract
surface used by test/surrogate backends. A live HLA adapter also overrides the
otherwise optional lifecycle/declaration hooks and invokes `_emit` from its
RTI receive callback. Common direction checks, codec calls, callback dispatch,
state tracking, and idempotent close are inherited.

### Required (abstract)

```python
def _do_send(self, binding, wire, timestamp) -> None
def _do_request_time_advance(self, target: float) -> float   # returns granted
```

### Optional (default no-op — override if the RTI needs them)

```python
def _do_join(self, federation, federate_name, fom_paths) -> None
def _do_publish(self, binding) -> None
def _do_subscribe(self, binding) -> None
def _do_resign(self) -> None
def _do_close(self) -> None
```

### Provided by the base (do **not** re-implement)

- `send(binding, payload, *, timestamp=None)` — drops `direction="in"`
  bindings, runs `codec.encode`, calls `_do_send`.
- `on_receive(cb)` — stores the single subscriber (the `_HLARouter`).
- `_emit(kind, fom_id, wire, timestamp=None)` — **the backend RX hook**:
  call it from your receive thread; it runs `codec.decode` and dispatches to
  the callback. Thread-safe downstream (`insert_external_event` takes a lock).
- `request_time_advance`, `join`, `publish`, `subscribe`, `resign`, `close`,
  `joined` — public surface; they call the `_do_*` hooks and maintain state
  (`publish`/`subscribe` before `join` raises `RuntimeError`; publishing an
  inbound-only binding or subscribing an outbound-only binding raises
  `ValueError`; `close` auto-resigns and is idempotent).

## 3. Adding a backend in 4 steps

```python
# my_rti.py
from pyjevsim.hla import RTIConnector, RTICapabilities, register_rti

class MyRTI(RTIConnector):
    capabilities = RTICapabilities(
        name="myrti", time_management=True, timestamp_ordered=True,
        interactions=True, object_attributes=True, default_lookahead=1.0,
    )

    def __init__(self, codec=None, **opts):
        super().__init__(codec)            # codec defaults to IdentityCodec
        # ... open sockets / load the RTI client / start RX thread ...

    # 1) outbound
    def _do_send(self, binding, wire, timestamp):
        # binding.kind in {"interaction","attribute"}, binding.fom_id is the
        # FOM id, wire is codec-encoded. Ship it (sendInteraction / update...).
        ...

    # 2) time advance (block until granted; return granted logical time)
    def _do_request_time_advance(self, target):
        ...                                # e.g. timeAdvanceRequest + wait grant
        return granted

    # 3) lifecycle (only what you need)
    def _do_join(self, federation, federate_name, fom_paths): ...
    def _do_publish(self, binding): ...
    def _do_subscribe(self, binding): ...
    def _do_resign(self): ...
    def _do_close(self): ...

    # 4) inbound: from your RX thread, when data arrives, call:
    #        self._emit(kind, fom_id, wire, timestamp)

# register so apps can select it by name without importing the class
register_rti("myrti", lambda **kw: MyRTI(**kw))
```

Select the backend while keeping a compatible model class unchanged. The
executor factory, bindings, and lifecycle calls remain part of the setup:

```python
from pyjevsim import SysExecutor, ExecutionType
from pyjevsim.hla import create_rti, HLAExecutorFactory, Federate
import my_rti  # noqa: F401  (registers "myrti")

transport = create_rti("myrti", host="...", fom="Chat.xml")
sys_exec  = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
sys_exec.exec_factory = HLAExecutorFactory(transport, bindings_by_model)

fed = Federate(sys_exec, transport)
fed.join("MyFederation", "alice", fom_paths=["Chat.xml"])
fed.run_until(end_time=60.0, lookahead=1.0)
```

## 4. Codec — FOM encoding is orthogonal

`send`/`_emit` route the payload through a `Codec`:

```python
class Codec(Protocol):
    def encode(self, binding, payload) -> Any   # payload is SysMessage.retrieve() (a list)
    def decode(self, kind, fom_id, wire) -> Any
```

The default `IdentityCodec` passes objects through (in-process / loopback).
A live RTI adapter supplies a codec that maps to FOM datatypes, such as an HLA 1516e
codec built on the `EncoderFactory` (`HLAfixedRecord`, `HLAinteger32BE`, …).
Because the codec is injected (`MyRTI(codec=...)`), one FOM codec can be
reused across RTIs, and one RTI can carry different FOMs.

## 5. Capabilities — information for callers

`RTICapabilities` lets callers branch on what a backend supports:

| flag | meaning |
|------|---------|
| `time_management` | some regulating/constrained logical-time service is available; consult the backend service matrix for TAR/NER coverage |
| `timestamp_ordered` | TSO delivery (vs receive-order RO) |
| `interactions` / `object_attributes` | interaction vs object-attribute classes |
| `ddm` / `ownership` | data distribution / ownership management |
| `default_lookahead` | suggested lookahead if the app doesn't set one |

E.g. an app may refuse to use `HLAAttribute` bindings against a backend whose
`object_attributes` is `False`, or skip passing timestamps when
`timestamp_ordered` is `False`.

These flags are descriptive metadata; the base connector does not negotiate
features with an RTI or automatically reject every unsupported operation.
`InProcessRTI`, for example, advertises neither time management nor TSO because
it returns identity grants and relies on the application to drive lock-step.

## 6. Threading & time

- **Outbound** runs on the simulation thread (inside `SysExecutor.step` →
  `HLAExecutor.output` → `send`). Keep `_do_send` non-blocking where possible.
- **Inbound** arrives on the backend's RX thread; `_emit` →
  `insert_external_event` is lock-protected, so no extra locking is needed in
  the model. Carry the **logical timestamp** through `_emit` so inbound events
  enter the intended simulated instant. The `SysExecutor.step` /
  `_run_instant` path invokes `con_trans` when an inbound event coincides
  with an imminent model.
- **Time advance** is logical-only. `Federate.run_until` enforces a positive
  request increment (its second argument is historically named `lookahead`)
  and loops `request_time_advance(target)` → `step(granted)` until
  `global_time >= end_time`. The backend owns the separate HLA regulating
  interval and time-unit mapping: Pitch uses its configured lookahead, while
  Portico uses one internal RTI sub-step. A backend may grant `≤ target`.

## 7. Concrete backends (where they live)

Backends register themselves on import so their dependencies stay optional:

| RTI | repository status/how | dependency |
|-----|-----|------------|
| `loopback` | shipped test backend (`transport.py`) | none |
| Pitch pRTI 1516e | shipped JPype backend | `jpype1` + `prti1516e.jar` + CRC |
| Portico 1516e | shipped JPype backend; subclasses Pitch (`backends/portico.py`) | `jpype1` + `portico.jar` (no CRC) |
| CERTI | not shipped; possible Python binding or surrogate extension | CERTI libs |
| OpenRTI / MÄK | not shipped; possible JPype/JNI or surrogate extension | vendor libs |

`backends/pitch.py` uses the `hla.rti1516e` Java API discovered through
`RtiFactoryFactory`. `backends/portico.py` subclasses that implementation and
overrides four extension hooks: `_encode_value` and `_decode_value` for its
standard-layout `HLAunicodeString` path, and `_rti_time` and `_rti_lookahead`
for its internal time mapping. Portico returns the tested reflections in
receive order, so the adapter uses a three-sub-step barrier. The barrier
prevents next-tick over-read; current-batch completeness still depends on the
configured `quiet` and `settle` waits.
