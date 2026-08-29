# IEEE 1516 service coverage

pyjevsim is **IEEE 1516-2010-based** and implements the subset needed to run
DEVS models as time-managed federates.  It is not certified as a conforming RTI
or a complete implementation of the IEEE 1516 service groups.

The table describes the concrete Pitch, Portico, and GORTI adapters.
`InProcessRTI` and `LoopbackTransport` are deterministic test backends, not
IEEE RTIs.

The GORTI entries describe the experimental, source-installed adapter shipped
in v2.2.0. They are scoped functional observations, not release-grade support.

| Service area | Status | Implementation and tests |
|---|---|---|
| Connect/disconnect | Implemented | Pitch/Portico use Java `hla.rti1516e`; GORTI uses its native Python `Rti1516eAmbassador`; close is idempotent |
| Create federation | Implemented | `FederationExecutionAlreadyExists` is accepted; other creation/FOM exceptions propagate |
| Join federation | Implemented | joins with a federate name/type and FOM modules |
| Resign/destroy federation | Implemented with best-effort cleanup | Pitch/Portico use `DELETE_OBJECTS_THEN_DIVEST`; GORTI uses `CANCEL_THEN_DELETE_THEN_DIVEST`; expected cleanup failures are suppressed |
| Publish/subscribe interactions | Implemented | handle resolution, declaration, TSO send, receive callback; exercised by ping-pong tests |
| Publish/subscribe object attributes | Implemented for the scoped binding path | instance registration, attribute update, discovery/reflection; exercised by ping-pong and AT/SIM; not complete Object Management |
| Object-instance lifecycle | Partial | one registered instance per outbound attribute binding/FOM id; no public multi-instance or explicit delete-object API |
| Time regulation/constrained | Implemented for live adapters | Pitch/Portico require both activation callbacks; GORTI invokes the corresponding native SDK services; Pitch/GORTI use configured lookahead, Portico one RTI sub-step |
| Time advance request/grant | TAR/TAG implemented | blocking `timeAdvanceRequest`/grant callback; GORTI exposes a configurable grant timeout; no NER or cancellation |
| Timestamp-ordered delivery | Pitch/GORTI: implemented; Portico: RO adaptation | Pitch and GORTI carry timestamps directly; Portico advertises `timestamp_ordered=False` and uses a buffered tick barrier whose current-batch completeness depends on `quiet`/`settle` timing |
| Federation synchronization points | Pitch/Portico only | register, wait for announcement, achieve, wait for federation synchronization; validated only by the multiprocess Pitch ping-pong example; not exposed by the GORTI connector |
| FOM field codec | Partial | `HLAinteger32BE`, `HLAinteger64BE`, `HLAfloat64BE`, `HLAunicodeString`; live send maps the first record in the payload list |
| Data distribution management | Not implemented | capability flag is false |
| Ownership management | Not implemented | capability flag is false |
| Message retraction | Not implemented | no connector API |
| Federation save/restore | Not implemented | use an RTI facility directly; HLA executor snapshots are unsupported |
| Management Object Model services | Not implemented | no connector API |
| Formal conformance test suite | Not performed | validation covers the listed service paths only |

## Binding directions

Bindings accept exactly three directions:

- `in`: subscribe/receive only; an attempted outbound `send` is ignored;
- `out`: publish/send only; no inbound route is installed; and
- `inout`: installs both paths.

Any other direction raises `ValueError` when the binding is constructed.
Bindings that name a model port not declared in the corresponding input/output
port set also raise `ValueError` during `HLAExecutor` construction.
Calling `publish` with an `in` binding or `subscribe` with an `out` binding
raises `ValueError`; an `inout` binding is accepted by both operations.

Lifecycle order is checked separately: `publish` and `subscribe` before
`join` raise `RuntimeError`, a duplicate `join` raises `RuntimeError`, `resign`
is a no-op when not joined, and `close` is idempotent and auto-resigns.

The HLA unit tests cover binding construction, publish/subscribe direction,
data routing, and connector lifecycle behavior under
[`tests/hla/`](../../tests/hla/).

## Error propagation policy

- Invalid binding directions, invalid publish/subscribe direction, undeclared
  bound model ports, and invalid lifecycle order fail before an RTI call.
- A federation that already exists is treated as a normal concurrent-start case.
- Bad FOMs, missing handles, codec errors, join failures, send failures, and
  time-advance failures propagate to the caller.
- Missing Pitch/Portico time-regulation or time-constrained activation
  callbacks raise `TimeoutError`; a missing GORTI time grant raises
  `TimeoutError` when its optional timeout is configured.
- Resign, federation destruction, and disconnect are best-effort cleanup and
  intentionally suppress backend exceptions.
- No automatic retry or reconnect policy is implemented.
- Individual live drivers may self-skip when Java/JAR support, the GORTI SDK,
  or a reachable `rtid` is absent; the live equivalence verifier treats a
  missing trace as an error (status 2).

Capability flags are descriptive metadata, not automatic service negotiation.
Check this matrix together with the selected backend's documentation when a
service detail affects an application.
