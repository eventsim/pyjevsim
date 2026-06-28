# pyjevsim HLA Subsystem — Specification

This document is the **contract**. The test suite encodes it. Implementations
must satisfy it. Where a test contradicts this document, the document is
authoritative — fix the test, or fix the spec, but do not let them drift.

## 1. Bindings (M0)

### 1.1 `HLAInteraction`

```python
@dataclass(frozen=True)
class HLAInteraction:
    fom_id: str                                     # e.g. "Communication.ChatMsg"
    direction: Literal["in", "out", "inout"] = "out"
    kind: str = "interaction"                       # constant; never overridden
```

- `fom_id` is opaque to pyjevsim — only the `Transport` interprets it.
- `direction="in"` means inbound only (subscribe). `"out"` means outbound
  only (publish). `"inout"` does both.

### 1.2 `HLAAttribute`

```python
@dataclass(frozen=True)
class HLAAttribute:
    fom_id: str                                     # e.g. "Vehicle.position"
    direction: Literal["in", "out", "inout"] = "out"
    kind: str = "attribute"
    object_class: str | None = None
```

- For an outbound attribute update, `object_class` is required.
- For an inbound reflect, `object_class` may be `None`; the transport
  resolves it from the wire payload.

### 1.3 Both classes

- `frozen=True` — bindings are hashable and used as dict keys. Required.
- `eq=True` (default) — bindings with identical fields compare equal.

## 2. Transport (M0)

### 2.1 Protocol

```python
class Transport(Protocol):
    def send(self, binding, payload) -> None: ...
    def on_receive(self, callback) -> None: ...
    def request_time_advance(self, target: float) -> float: ...
    def close(self) -> None: ...
```

- `send(binding, payload)` is called by `HLAExecutor.output`. Synchronous.
  `payload` is **always** the result of `SysMessage.retrieve()` — a list
  of items the model `insert()`-ed, never a single dict. Errors raise;
  caller decides how to surface.
- `on_receive(cb)` registers a callback `cb(kind, fom_id, payload, timestamp)`
  invoked whenever the transport delivers an inbound event. May be called
  from any thread. **Single-callback contract**: re-registering replaces.
  Per-executor dispatch is the responsibility of `_HLARouter` (§2.3),
  not of the transport.
- `request_time_advance(target)` blocks until the RTI grants. Returns the
  granted logical time, which may be ≤ target. Only `Federate` calls it.
- `close()` releases resources. Idempotent.

### 2.2 `LoopbackTransport` (M0, test-only)

In-process transport that delivers every `send(binding, payload)` to its
own `on_receive` callback after rewriting `direction`:
- A binding with `direction="out"` is mirrored to a binding with the same
  `fom_id` and `direction="in"`. The `payload` (list) is forwarded as-is.
- A binding with `direction="in"` passed to `send` is dropped (loopback
  only mirrors out→in).
- Two `LoopbackTransport` instances may be cross-wired so federate A's
  outputs become federate B's inputs.

`request_time_advance(target)` returns `target` immediately (no flow
control, no lookahead enforcement). `close()` is a no-op.

### 2.3 `_HLARouter` (M0, internal)

The router is the *single* subscriber on a `Transport`. It demultiplexes
inbound events to the right `HLAExecutor` based on `(kind, fom_id)`.

```python
class _HLARouter:
    def __init__(self, transport: Transport):
        self._transport = transport
        self._subs: dict[tuple[str, str], list[HLAExecutor]] = {}
        transport.on_receive(self._dispatch)

    def subscribe(self, kind: str, fom_id: str, executor) -> None: ...
    def unsubscribe(self, kind: str, fom_id: str, executor) -> None: ...
    def _dispatch(self, kind, fom_id, payload, timestamp) -> None:
        for ex in self._subs.get((kind, fom_id), ()):
            ex._on_rti_event(kind, fom_id, payload, timestamp)
```

- One router per transport. The factory (M2) constructs it.
- Multiple executors may subscribe to the same `(kind, fom_id)`; all
  receive the event.
- `_dispatch` is called from the transport's RX thread; subscribers
  must be safe to invoke from there. `HLAExecutor._on_rti_event` is
  safe because it only calls `parent.insert_external_event`, which is
  lock-protected (`system_executor.py:833`).

## 3. `HLAExecutor` (M1)

### 3.1 Class

```python
class HLAExecutor(BehaviorExecutor):
    def __init__(self, itime, dtime, ename, behavior_model, parent,
                 transport, bindings, router): ...
```

- Inherits from `BehaviorExecutor`. Overrides only `output` and
  `__init__`.
- `bindings: dict[str, HLAInteraction | HLAAttribute]` keyed by port name.
- `parent` is the owning `SysExecutor` (per pyjevsim's existing
  `Executor` contract — `register_entity` passes `self`). Used directly;
  no separate `sys_executor` arg.
- `router` is the shared `_HLARouter` (§2.3); the executor calls
  `router.subscribe(...)` for every in/inout binding during construction.

### 3.2 Output interception (the central rule)

When `SysExecutor` calls `executor.output(msg_deliver)`:

1. Run the wrapped model's `output(inner)` against a **private**
   `MessageDeliverer`.
2. For each `SysMessage` in `inner`:
   - If its destination port has a binding with `direction in {"out","inout"}`,
     call `transport.send(binding, sys_msg.retrieve())` and **drop** the
     message from the outer bag.
   - Otherwise, forward the message to the outer `msg_deliver` (normal
     local coupling path).

Bound `out` ports are **exclusively** RTI endpoints — they do not also
fan out via `port_map`. Documented; tested.

### 3.3 Construction-time wiring

For every binding with `direction in {"in", "inout"}`, the constructor
does four things:

1. Compute a **namespaced SE-side port name** to avoid collisions
   between models that share a model-side port name:

   ```python
   sys_port = f"_hla_{behavior_model.get_obj_id()}__{model_port}"
   ```

2. Register the SE-side port on `parent`:

   ```python
   if sys_port not in parent.retrieve_input_ports():
       parent.insert_input_port(sys_port)
   ```

3. Add a coupling so events injected on the SE-side port reach the
   model:

   ```python
   parent.coupling_relation(None, sys_port, behavior_model, model_port)
   ```

4. Build the inbound route table and subscribe via the router:

   ```python
   self._inbound_routes[(binding.kind, binding.fom_id)] = (sys_port, model_port)
   router.subscribe(binding.kind, binding.fom_id, self)
   ```

Without all four steps, `insert_external_event` (`system_executor.py:832`)
silently drops the event with a print — the port lookup against
`external_input_ports` fails. Tested by M1.7 end-to-end.

### 3.4 Inbound injection

When the router invokes the executor's callback:

```python
def _on_rti_event(self, kind, fom_id, payload, timestamp):
    route = self._inbound_routes.get((kind, fom_id))
    if route is None:
        return                                          # not subscribed
    sys_port, _model_port = route
    now = self.parent.global_time
    delay = max(0.0, (timestamp if timestamp is not None else now) - now)
    self.parent.insert_external_event(sys_port, payload, scheduled_time=delay)
```

- `insert_external_event` is already thread-safe (`system_executor.py:833`
  takes `self.condition`). No new locking required in `HLAExecutor`.
- `delay` clamps to `[0, ∞)` — events stamped in the past land at the
  current global time.

### 3.5 Pass-through methods

`ext_trans`, `int_trans`, `con_trans`, `time_advance`, `set_req_time`,
`get_req_time` are **not overridden**. The grant ceiling is enforced by
`SysExecutor.step` itself.

### 3.6 Errors

- Constructor with `bindings={}` is legal (degenerate; behaves like a
  plain `BehaviorExecutor`).
- A binding referencing a port not declared on the model raises
  `ValueError` at construction time.
- Transport `send` failures propagate to the caller of `output()`.
  `HLAExecutor` does not retry. Document for transport authors.

## 4. `HLAExecutorFactory` (M2)

### 4.1 Class

```python
class HLAExecutorFactory(ExecutorFactory):
    def __init__(self, transport, bindings_by_model: dict[str, dict[str, Binding]]): ...
    def create_behavior_executor(self, _, ins_t, des_t, en_name, model, parent): ...
```

- `bindings_by_model[model_name]` lists bindings for that model. Models
  not in the dict get a plain `BehaviorExecutor`.
- `parent` is the `SysExecutor`. Stored on the produced `HLAExecutor`.

### 4.2 Wiring

Users opt in by replacing the factory **after** `SysExecutor`
construction:

```python
sys_exec = SysExecutor(time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
sys_exec.exec_factory = HLAExecutorFactory(transport, bindings_by_model)
```

This keeps the core `SysExecutor` API unchanged. (M2 makes one tiny
ergonomic addition — see §4.3 — but never breaks the constructor.)

### 4.3 Optional convenience: `set_executor_factory`

For discoverability, M2 may add `SysExecutor.set_executor_factory(factory)`
that simply assigns `self.exec_factory`. Optional; tests do not require it.

## 5. `Federate` runtime (M3)

### 5.1 Class

```python
class Federate:
    def __init__(self, sys_executor, transport): ...
    def join(self, federation_name, federate_name, fom_paths) -> None: ...
    def publish(self, binding) -> None: ...
    def subscribe(self, binding) -> None: ...
    def resign(self) -> None: ...
    def run_until(self, end_time, lookahead) -> None: ...
```

### 5.2 Lifecycle method semantics

Each method is a thin pass-through that the transport implements. The
`Federate` class:
- **Validates argument shape** (e.g. `lookahead > 0`).
- **Maintains state** (joined / not joined). Calling `publish` before
  `join` raises `RuntimeError`.
- Does **not** call RTI services itself — it delegates to the transport.

### 5.3 The grant loop

```python
def run_until(self, end_time, lookahead):
    if lookahead <= 0:
        raise ValueError("lookahead must be > 0")
    while self._sys.global_time < end_time:
        target = min(self._sys.global_time + lookahead, end_time)
        granted = self._tx.request_time_advance(target)
        self._sys.step(granted)
```

- Granted time may be ≤ target. Loop terminates when
  `global_time ≥ end_time`.
- `step(granted)` updates `global_time` per
  `system_executor.py:781` (post-step it equals `granted`).
- The federate does not pace to wallclock. HLA_TIME is logical only.

## 6. Confluent semantics (M4)

### 6.1 Required core patch (M4.0)

`SysExecutor.step`'s round loop currently consults only
`min_schedule_item` when computing `next_t` (`system_executor.py:716`).
External events with timestamps inside the grant window stay queued
until the next `step()` call advances `global_time` past them — this
breaks IEEE 1516 TSO delivery.

**Fix** — extend the round-loop peek to also consult
`input_event_queue`:

```python
# system_executor.py — inside step(granted_time)
while self.min_schedule_item or self.input_event_queue:
    next_internal = self.min_schedule_item.peek_time(default=Infinite)
    next_external = (self.input_event_queue[0][0]
                     if self.input_event_queue else Infinite)
    next_t = min(next_internal, next_external)
    if next_t > granted_time:
        break
    if next_t > self.global_time:
        self.global_time = next_t
    self.handle_external_input_event()
    imminent = self.min_schedule_item.pop_all_at(next_t)
    if not imminent and not self.input_event_queue:
        continue
    ...
```

This is a **core-touching change** (~10 LOC). Implemented as task M4.0
before any of M4.1–M4.5. The full pyjevsim suite (V_TIME, R_TIME,
HLA_TIME) must continue to pass after the patch.

### 6.2 Resulting semantics

- An event delivered via `insert_external_event(port, payload, t)` with
  `t ≤ granted_time` fires at simulated time `t` during the current
  `step` call.
- A model receiving such an event while imminent gets `con_trans`, not
  separate `int_trans` then `ext_trans`.
- Events with `t > granted_time` stay queued and fire on the next
  `step()` call whose grant covers their timestamp.

## 7. Snapshot composition

**Deferred to v2.** Adding an `is_snapshottable()` hook to
`SnapshotExecutor` and `SnapshotManager` is core work that does not
pay back in v1. Until then:

- HLA federates **are not snapshot-able** in v1.
- Wrapping an `HLAExecutor` in a `SnapshotExecutor` has undefined
  behavior. Don't.
- Use the RTI's federation save/restore service for federate
  persistence. (Out of scope here; gorti M11 / future kdx-rti work.)

## 8. Public exports (`pyjevsim.hla.__init__`)

```python
from .bindings import HLAInteraction, HLAAttribute
from .transport import Transport, LoopbackTransport
from .hla_executor import HLAExecutor
from .factory import HLAExecutorFactory
from .federate import Federate
```

## 9. Non-goals (will not be implemented under this plan)

- A new base class for federate models (rejected — would pollute
  `BehaviorModel` with implementation detail).
- Decorators like `@publishes("Foo")` (sugar; defer until users ask).
- A `WAKE_PORT` analogue on `SysExecutor` (unnecessary —
  `HLAExecutor` calls `insert_external_event` directly).
- Real-time pacing under HLA_TIME (use `R_TIME` if you want wallclock).
