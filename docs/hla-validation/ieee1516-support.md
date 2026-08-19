# IEEE 1516 service coverage

pyjevsim is **IEEE 1516-2010-based** and implements the subset needed to run
DEVS models as time-managed federates.  It is not certified as a conforming RTI
or a complete implementation of the IEEE 1516 service groups.

The table describes the concrete Pitch/Portico adapter.  `InProcessRTI` and
`LoopbackTransport` are deterministic test backends, not IEEE RTIs.

| Service area | Status | Implementation and test boundary |
|---|---|---|
| Connect/disconnect | Implemented | Java `hla.rti1516e` ambassador connection; close is idempotent and suppresses disconnect failures |
| Create federation | Implemented | `FederationExecutionAlreadyExists` is accepted; other creation/FOM exceptions propagate |
| Join federation | Implemented | joins with a federate name/type and FOM modules |
| Resign/destroy federation | Implemented with best-effort cleanup | resign uses `DELETE_OBJECTS_THEN_DIVEST`; expected Java cleanup failures are suppressed |
| Publish/subscribe interactions | Implemented | handle resolution, declaration, TSO send, receive callback; exercised by ping-pong tests |
| Publish/subscribe object attributes | Implemented | instance registration, attribute update, discovery/reflection; exercised by ping-pong and AT/SIM |
| Object-instance lifecycle | Partial | one registered instance per outbound attribute binding/FOM id; no public multi-instance or explicit delete-object API |
| Time regulation/constrained | Implemented for live adapters | both activation callbacks must arrive within 10 s or `TimeoutError` is raised; Pitch uses configured lookahead, Portico one RTI sub-step |
| Time advance request/grant | TAR/TAG implemented | blocking `timeAdvanceRequest`/grant callback; no NER, generic timeout, or cancellation |
| Timestamp-ordered delivery | Pitch: implemented; Portico: RO adaptation | Pitch carries timestamps directly; Portico advertises `timestamp_ordered=False` and uses a buffered tick barrier whose current-batch completeness depends on `quiet`/`settle` timing |
| Federation synchronization points | Implemented in Pitch base, inherited by Portico | register, wait for announcement, achieve, wait for federation synchronization; validated only by the multiprocess Pitch ping-pong example |
| FOM field codec | Partial | `HLAinteger32BE`, `HLAinteger64BE`, `HLAfloat64BE`, `HLAunicodeString`; live send maps the first record in the payload list |
| Data distribution management | Not implemented | capability flag is false |
| Ownership management | Not implemented | capability flag is false |
| Message retraction | Not implemented | no connector API |
| Federation save/restore | Not implemented | use an RTI facility directly; HLA executor snapshots are unsupported |
| Management Object Model services | Not implemented | no connector API |
| Formal conformance test suite | Not performed | validation covers the listed interoperability paths only |

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
is harmless when not joined, and `close` is idempotent and auto-resigns.

The direction and lifecycle behavior is covered by
[`tests/hla/test_m0_foundation.py`](../../tests/hla/test_m0_foundation.py),
[`tests/hla/test_m1_data_path.py`](../../tests/hla/test_m1_data_path.py), and
[`tests/hla/test_rti_interface.py`](../../tests/hla/test_rti_interface.py).

## Error propagation policy

- Invalid binding directions, invalid publish/subscribe direction, undeclared
  bound model ports, and invalid lifecycle order fail before an RTI call.
- A federation that already exists is treated as a normal concurrent-start case.
- Bad FOMs, missing handles, codec errors, join failures, send failures, and
  time-advance failures propagate to the caller.
- Missing time-regulation or time-constrained activation callbacks raise
  `TimeoutError` and trigger best-effort resignation.
- Resign, federation destruction, and disconnect are best-effort cleanup and
  intentionally suppress backend exceptions.
- No automatic retry or reconnect policy is implemented.
- Individual live drivers may self-skip when Java/JAR support is absent; the
  live equivalence verifier treats a missing trace as an error (status 2).

Capability flags are descriptive metadata, not automatic service negotiation.
The matrix and backend documentation are authoritative when a finer distinction
is needed.
