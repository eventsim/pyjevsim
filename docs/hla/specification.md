# HLA design reference

The pyjevsim HLA path separates model-port bindings, the executor bridge,
codecs, and the selected RTI connector. Transport adapters follow the
behavior described below. For practical setup, see the
[developer guide](instruction.md). For the backend extension API, see
[RTI backend interface](rti_interface.md).

## 1. Bindings

`HLAInteraction` and `HLAAttribute` associate a named model port with a
Federation Object Model (FOM) identifier.

```python
HLAInteraction(fom_id: str, direction: Literal["in", "out", "inout"] = "out")
HLAAttribute(
    fom_id: str,
    direction: Literal["in", "out", "inout"] = "out",
    object_class: str | None = None,
)
```

- `in` bindings receive subscribed data.
- `out` bindings publish model output.
- `inout` bindings support both paths.
- Any other direction raises `ValueError` during construction.
- `kind` is fixed by the binding class as `interaction` or `attribute`.
- `object_class` is optional metadata for custom transports. The built-in
  live adapters resolve object classes from their FOM maps.

Bindings are immutable and may be used as dictionary keys.

## 2. Transport and connector

The structural `Transport` protocol contains the data, callback, time, and
cleanup operations used by the executor:

```python
class Transport(Protocol):
    def send(self, binding, payload) -> None: ...
    def on_receive(self, callback) -> None: ...
    def request_time_advance(self, target: float) -> float: ...
    def close(self) -> None: ...
```

New backends should subclass `RTIConnector`. It adds lifecycle methods,
direction checks, codec dispatch, a single inbound callback, and idempotent
cleanup. A minimal in-memory backend implements:

```python
def _do_send(self, binding, wire, timestamp) -> None: ...
def _do_request_time_advance(self, target: float) -> float: ...
```

A live backend also implements the applicable join, declaration, resign, and
disconnect hooks, and calls `_emit(kind, fom_id, wire, timestamp)` from its
receive callback.

`send()` accepts only `out` and `inout` bindings. Directly passing an `in`
binding to `send()` produces no outbound message. `publish()` and
`subscribe()` require a joined connector and reject incompatible directions.

### 2.1 Payload and codec

On the outbound path, the payload is the list returned by
`SysMessage.retrieve()`. The connector encodes it before calling `_do_send`.
On the inbound path, `_emit` decodes the backend value and calls the registered
receiver with:

```text
(kind, fom_id, payload, timestamp)
```

`IdentityCodec` passes Python objects through for local backends. Pitch and
Portico map supported values to HLA datatypes. Their current scalar support is
listed in the [service matrix](../hla-validation/ieee1516-support.md).

### 2.2 Inbound routing

`_HLARouter` is the connector's single callback target. It routes an inbound
event to every `HLAExecutor` subscribed to the matching `(kind, fom_id)` pair.
One `HLAExecutorFactory` owns one router for its connector.

### 2.3 Local backends

`LoopbackTransport` reflects outbound data to its own callback and returns
requested time grants unchanged. `InProcessRTI` broadcasts synchronously to
other connectors in the same in-process federation and also returns requested
grants unchanged. These backends do not coordinate federation-wide logical
time and are intended for tests and local examples.

## 3. HLAExecutor

`HLAExecutor` wraps a `BehaviorModel` without adding HLA calls to the model
class. Its `bindings` dictionary maps model port names to binding objects.

During construction it checks that:

- `in` and `inout` bindings refer to declared input ports; and
- `out` and `inout` bindings refer to declared output ports.

An unknown port raises `ValueError`.

### 3.1 Outbound data

For each message produced by the model:

1. If the destination port has an `out` or `inout` binding,
   `HLAExecutor` sends the retrieved payload through the connector.
2. Otherwise, it passes the message to the normal local coupling path.

A bound outbound port is RTI-only. Use a separate output port when the same
logical value must also be delivered through a local coupling.

### 3.2 Inbound data

For each `in` or `inout` binding, `HLAExecutor` creates a namespaced input on
the owning `SysExecutor`, couples it to the model port, and subscribes through
`_HLARouter`.

An inbound timestamp is converted to a delay relative to the current
simulation time. A timestamp in the past is clamped to the current time. Each
payload item is then inserted through `SysExecutor.insert_external_event`,
which uses the normal external-event and confluent-transition path.

## 4. HLAExecutorFactory

Users install `HLAExecutorFactory` on a `SysExecutor` before registering
models:

```python
sys_exec = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
sys_exec.exec_factory = HLAExecutorFactory(transport, bindings_by_model)
```

`bindings_by_model` is keyed by model name. A model with a non-empty entry gets
an `HLAExecutor`; other models use the ordinary `BehaviorExecutor`.

## 5. Federate lifecycle and grant loop

`Federate` delegates federation lifecycle and declarations to the connector:

```python
fed.join(federation_name, federate_name, fom_paths)
fed.publish(binding)
fed.subscribe(binding)
fed.run_until(end_time, lookahead)
fed.resign()
```

Publishing or subscribing before `join()` raises `RuntimeError`. The argument
historically named `lookahead` in `run_until` is the positive increment between
requested grant targets; it is separate from a live backend's HLA regulating
lookahead.

The loop repeatedly requests the next target and advances the simulator to the
granted time:

```python
while sys_exec.global_time < end_time:
    target = min(sys_exec.global_time + lookahead, end_time)
    granted = transport.request_time_advance(target)
    sys_exec.step(granted)
```

Live backends may block while waiting for an RTI grant. The connector has no
general deadlock detector, retry policy, or reconnect mechanism.

## 6. Logical-time and confluent behavior

`SysExecutor.step(granted_time)` processes internal and external events whose
time is at or before the grant. Events at the same simulated instant are
collected before transitions are applied:

- imminent model with input: `con_trans`;
- imminent model without input: `int_trans`;
- non-imminent model with input: `ext_trans`.

Zero-time cascades at the same instant complete within the call. After the
call, `global_time` equals the granted time.

Pitch maps pyjevsim time directly to HLA time and uses TAR/TAG with timestamped
sends. Portico maps one caller tick to three RTI sub-steps and buffers
receive-order reflections before exposing the current tick. Its batch
completeness depends on the configured quiet and settle waits. The detailed
behavior is in the [validation guide](../hla-validation/README.md#6-hla-time-management).

## 7. Threading and error handling

- Model transitions and outbound calls run on the simulation thread.
- Backend callbacks may run on an RTI-owned thread.
- Inbound delivery enters `SysExecutor.insert_external_event`, which is
  protected for concurrent callback use.
- Binding, port, lifecycle, codec, handle, and synchronous send errors normally
  propagate to the caller.
- `close()` is idempotent. Cleanup attempts to resign first; individual live
  backend cleanup errors may be suppressed so remaining resources can close.
- No automatic resend, retry, or reconnect is provided.

## 8. Supported scope

The connector covers a documented subset of IEEE 1516-2010 services. It does
not provide data distribution management, ownership management, message
retraction, federation save/restore, or a formal conformance layer. HLA
executors are not supported by the model snapshot mechanism.

See the [service coverage table](../hla-validation/ieee1516-support.md) and
[known limitations](../hla-validation/README.md#8-limitations-and-future-work)
before selecting a backend for an application.

## 9. Source map

| Component | Source |
|---|---|
| Bindings | `pyjevsim/hla/bindings.py` |
| Connector, codec, router | `pyjevsim/hla/transport.py` |
| Model bridge | `pyjevsim/hla/hla_executor.py` |
| Executor factory | `pyjevsim/hla/factory.py` |
| Federate loop | `pyjevsim/hla/federate.py` |
| Pitch backend | `pyjevsim/hla/backends/pitch.py` |
| Portico backend | `pyjevsim/hla/backends/portico.py` |
| Simulation grant processing | `pyjevsim/system_executor.py` |
