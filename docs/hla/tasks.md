# pyjevsim HLA Subsystem — Task Breakdown

Each task below is a self-contained unit an agent can complete in one
session. Tasks are ≤80 LOC of code or ≤120 LOC of tests, touch 1–2
files, and are validated by a single `pytest` invocation. Do them in
order; later tasks assume earlier ones are merged.

The pre-work block (PW) addresses the five blockers found during the
plan review (`docs/hla/specification.md` review, see commit log). Do
PW.* before starting M0 — without these the spec contradicts pyjevsim's
actual core, and M1+ implementations will hit unrecoverable wiring
problems.

---

## Pre-work — Spec & test corrections

### PW.1 — Inbound wiring: namespaced ports + couplings (spec rewrite)

**Why**: `SysExecutor.insert_external_event` (`system_executor.py:832`)
silently drops events for ports not in `external_input_ports`.
Routing requires both `insert_input_port` on the SE *and* a
`coupling_relation`. Two models with the same port name collide on the
SE-side port. Spec §3.3 must be rewritten so `HLAExecutor.__init__`
performs the wiring and uses a namespaced SE-side port name like
`f"_hla_{obj_id}__{port_name}"`.

**Edit**: `docs/hla/specification.md` §3.1, §3.3.
Add a new §3.3a "Construction-time wiring" listing the steps.

**Acceptance**: spec text describes (a) namespaced SE port, (b)
coupling from `(None, sys_port) → (model, model_port)` for each
in/inout binding, (c) the `_inbound_routes` table maps
`(kind, fom_id) → (sys_port, model_port)`.

**LOC**: docs only, ~30 lines new.

---

### PW.2 — Shared `_HLARouter` dispatcher (spec rewrite)

**Why**: `Transport.on_receive` allows a single callback (§2.1). With
two `HLAExecutor`s on one transport the second registration replaces
the first. Need a shared dispatcher between the transport and the
per-model executors.

**Edit**: `docs/hla/specification.md` §2.1 (clarify single-callback is
the *transport's* contract; users should not register two), add §2.3
"`_HLARouter`" describing the new internal class. Update §3 so
`HLAExecutor` registers inbound routes on the router, not on the
transport directly.

**Acceptance**: spec describes
`_HLARouter.subscribe(kind, fom_id, executor)` and the routing
semantics. The router itself lives in `pyjevsim/hla/transport.py`.

**LOC**: docs only, ~25 lines.

---

### PW.3 — Drop M5 from v1 plan (RESOLVED — DROP)

**Decision**: confirmed by user — M5 deferred to v2.

**Done in this session** (no further work needed):
- `docs/hla/specification.md` §7 rewritten to one paragraph deferring
  to v2.
- `docs/hla/plan.md` milestone table marks M5 as DROP.
- `docs/hla/qa.md` M5 block replaced with a deferral notice.
- `tests/hla/test_m5_snapshot.py` deleted.

**Remaining work**: none.

---

### PW.4 — Fix `ConfluentCounter` test fixture

**Why**: With `deadline=0` and no state transition, the
`SysExecutor.step` round loop schedules the model back at t=0
infinitely. Hangs the test.

**Edit**: `tests/hla/conftest.py`. Add a `"done"` passive state and
transition into it from `int_trans` and `con_trans`.

**Acceptance**: a smoke test `step(0.0)` against a freshly-registered
`ConfluentCounter(deadline=0.0)` returns within 100 ms (use pytest's
`-x` and a deadline marker).

**LOC**: ~10 LOC change.

---

### PW.5 — Pin `Transport.send` payload shape

**Why**: M0.5 test asserts `payload == {"text": "hi"}` (dict); M1.4
test asserts `payload == [{"hello": "world"}]` (list from
`SysMessage.retrieve()`). Inconsistent contract.

**Edit**:
- `docs/hla/specification.md` §2.1: "`payload` is always the result of
  `SysMessage.retrieve()` — a list of inserted items."
- `tests/hla/test_m0_foundation.py` M0.5: pass `[{"text": "hi"}]` to
  `tx.send`, assert callback receives `[{"text": "hi"}]`.

**Acceptance**: spec says "list"; both M0.5 and M1.4 assert list shape.

**LOC**: ~5 lines docs, ~3 lines test.

---

### PW.6 — `step()` peek of `input_event_queue` (RESOLVED — option (a))

**Decision**: confirmed by user — patch `SysExecutor.step` to peek
`input_event_queue` alongside `min_schedule_item` when computing the
round loop's `next_t`. This restores correct TSO delivery.

**Done in this session** (spec):
- `docs/hla/specification.md §6.1` rewritten: explicit fix listed as
  required core patch (M4.0 task).
- `docs/hla/qa.md` M4 prerequisite line added: M4.0 must close before
  any M4.x test.

**Remaining work**: implementation in milestone M4 (task **M4.0**),
which is now non-conditional.

---

### PW.7 — Delete `test_m5_snapshot.py` (RESOLVED)

**Done in this session**: file deleted per PW.3.

---

## M0 — Foundation

### T0.1 — Package skeleton

**Files**: `pyjevsim/hla/__init__.py` (new).
**Body**: empty file with module docstring + the four public re-exports
(stub them to `None` for now; subsequent tasks fill in).
**Validation**: `python -c "import pyjevsim.hla"` succeeds.
**LOC**: ~10.
**Depends on**: PW.

---

### T0.2 — `bindings.py`

**Files**: `pyjevsim/hla/bindings.py` (new), update `__init__.py` exports.
**Body**: `HLAInteraction`, `HLAAttribute` frozen dataclasses per
spec §1.
**Validation**: `pytest tests/hla/test_m0_foundation.py::TestBindings -v`
→ M0.1, M0.2, M0.3 pass.
**LOC**: ~30.
**Depends on**: T0.1.

---

### T0.3 — `Transport` Protocol

**Files**: `pyjevsim/hla/transport.py` (new), update `__init__.py`.
**Body**: `Transport` typing.Protocol with the four methods per §2.1.
No implementations.
**Validation**: `pytest -k test_M0_4` passes.
**LOC**: ~20.
**Depends on**: T0.1.

---

### T0.4 — `LoopbackTransport`

**Files**: `pyjevsim/hla/transport.py` (extend).
**Body**: in-process transport. `send` mirrors `direction="out"` →
`"in"`, ignores `direction="in"`, calls registered callback if any.
`request_time_advance(t) → t`. `close()` idempotent.
**Validation**: `pytest -k "test_M0_5 or test_M0_6 or test_M0_7 or test_M0_8"` passes.
**LOC**: ~50.
**Depends on**: T0.2, T0.3.

---

### T0.5 — `_HLARouter` dispatcher

**Files**: `pyjevsim/hla/transport.py` (extend), `__init__.py`.
**Body**: per spec §2.3 (added in PW.2). API:
```python
class _HLARouter:
    def __init__(self, transport): ...           # registers single cb
    def subscribe(self, kind, fom_id, executor): ...
    def unsubscribe(self, kind, fom_id, executor): ...
    def _dispatch(self, kind, fom_id, payload, ts): ...
```
**Validation**: add 3 unit tests in `test_m0_foundation.py` (a
`TestHLARouter` class):
- subscribe + transport-side delivery → executor's callback called
- two executors subscribed to different `(kind, fom_id)` → only the
  right one fires
- unsubscribe → no further deliveries
**LOC**: code ~40, tests ~50.
**Depends on**: T0.4.

---

## M1 — HLAExecutor data path

### T1.1 — Class skeleton + constructor

**Files**: `pyjevsim/hla/hla_executor.py` (new), `__init__.py`.
**Body**: `HLAExecutor(BehaviorExecutor)`. `__init__(itime, dtime,
ename, behavior_model, parent, transport, bindings, router)`. Drop
`sys_executor` param (use `self.parent`, see I1). Store fields.
**Validation**: `pytest -k "test_M1_1 or test_M1_2"` passes.
**LOC**: ~40.
**Depends on**: T0.5.

---

### T1.2 — Binding validation

**Files**: same.
**Body**: in `__init__`, check every binding's port name against
`behavior_model.retrieve_input_ports()` (for in/inout) or
`retrieve_output_ports()` (for out/inout). Raise `ValueError` with
the offending port name.
**Validation**: `pytest -k test_M1_3` passes.
**LOC**: ~15.
**Depends on**: T1.1.

---

### T1.3 — Construction-time SE wiring

**Files**: `hla_executor.py`.
**Body**: per spec §3.3a (added in PW.1). For each binding with
direction in `{"in", "inout"}`:
1. Compute namespaced SE port name: `f"_hla_{behavior_model.get_obj_id()}__{port}"`.
2. `parent.insert_input_port(sys_port)` if not already present.
3. `parent.coupling_relation(None, sys_port, behavior_model, port)`.
4. Record `_inbound_routes[(binding.kind, binding.fom_id)] = (sys_port, port)`.
5. `router.subscribe(binding.kind, binding.fom_id, self)`.
**Validation**: no direct test yet (covered by T1.5 + T2.4 end-to-end);
but a smoke check that `parent.external_input_ports` contains the
namespaced port after construction.
**LOC**: ~30.
**Depends on**: T1.1, T1.2, T0.5.

---

### T1.4 — `output()` override

**Files**: `hla_executor.py`.
**Body**: per spec §3.2.
```python
def output(self, msg_deliver):
    inner = MessageDeliverer()
    self.behavior_model.output(inner)
    for sys_msg in inner.get_contents():
        port = sys_msg.get_dst()
        b = self._bindings.get(port)
        if b is not None and b.direction in ("out", "inout"):
            self._transport.send(b, sys_msg.retrieve())
            continue
        msg_deliver.insert_message(sys_msg)
```
**Validation**: `pytest -k "test_M1_4 or test_M1_5 or test_M1_6 or test_M1_10 or test_M1_11"` passes.
**LOC**: ~20.
**Depends on**: T1.1.

---

### T1.5 — Inbound dispatch (`_on_rti_event`)

**Files**: `hla_executor.py`.
**Body**: callback invoked by `_HLARouter._dispatch`. Looks up
`(kind, fom_id)` in `_inbound_routes`, computes
`delay = max(0.0, (timestamp or self.parent.global_time) - self.parent.global_time)`,
calls `self.parent.insert_external_event(sys_port, payload, delay)`.
**Validation**: `pytest -k "test_M1_7 or test_M1_8 or test_M1_9"`
passes. (Tests must be updated in PW to call `_on_rti_event` via the
router rather than directly on the executor; revise tests in this
task if PW didn't.)
**LOC**: ~25.
**Depends on**: T1.3.

---

## M2 — Factory + integration

### T2.1 — `HLAExecutorFactory` skeleton

**Files**: `pyjevsim/hla/factory.py` (new), `__init__.py`.
**Body**: subclass `ExecutorFactory`. Constructor takes `transport` and
`bindings_by_model: dict[str, dict[str, Binding]]`. Internally builds
a single `_HLARouter(transport)` and stores it.
**Validation**: `pytest -k test_M2_1` passes.
**LOC**: ~30.
**Depends on**: T1.5.

---

### T2.2 — `create_behavior_executor` override

**Files**: `factory.py`.
**Body**: override `create_behavior_executor`. If
`model.get_name() in bindings_by_model`, construct an `HLAExecutor`
with the router; else fall through to `BehaviorExecutor`. Reject
duplicate names with `ValueError` to avoid I2 silent collision.
**Validation**: `pytest -k "test_M2_2 or test_M2_3"` passes.
**LOC**: ~25.
**Depends on**: T2.1.

---

### T2.3 — Single-model end-to-end

**Files**: tests only.
**Body**: confirm `register_entity` + `step()` produces a
`transport.send` call. Test M2.4 + M2.5.
**Validation**: `pytest -k "test_M2_4 or test_M2_5"` passes.
**LOC**: tests already exist; no new code unless a bug surfaces.
**Depends on**: T2.2.

---

### T2.4 — Two-federate cross-wired

**Files**: tests only.
**Body**: alice OUT → loopback → bob IN. Verifies T0.5 router and
T1.3 wiring together. Test M2.6.
**Validation**: `pytest -k test_M2_6` passes.
**LOC**: test already exists.
**Depends on**: T2.3.

---

## M3 — Federate runtime

### T3.1 — `Federate` skeleton

**Files**: `pyjevsim/hla/federate.py` (new), `__init__.py`.
**Body**: class `Federate` storing `sys_executor` and `transport`.
`_joined: bool = False`.
**Validation**: `pytest -k test_M3_1` passes.
**LOC**: ~20.
**Depends on**: T2.4.

---

### T3.2 — Lifecycle methods + guard

**Files**: `federate.py`.
**Body**: `join`, `publish`, `subscribe`, `resign`. `publish` and
`subscribe` raise `RuntimeError` if `not self._joined`. Each method
delegates to the corresponding transport method.
**Validation**: `pytest -k "test_M3_2 or test_M3_3 or test_M3_4"` passes.
**LOC**: ~40.
**Depends on**: T3.1.

---

### T3.3 — `run_until` grant loop

**Files**: `federate.py`.
**Body**: loop `target = min(global_time + lookahead, end_time)` →
`granted = transport.request_time_advance(target)` →
`sys_exec.step(granted)`. Validate `lookahead > 0`.
**Validation**: `pytest -k "test_M3_5 or test_M3_6 or test_M3_7 or test_M3_8 or test_M3_9"` passes.
**LOC**: ~30.
**Depends on**: T3.2.

---

## M4 — Confluent semantics

### M4.0 — `SysExecutor.step` round-loop peek of `input_event_queue` (REQUIRED)

**Files**: `pyjevsim/system_executor.py` (modify), `tests/test_hla_step.py` (extend).

**Body**: per spec §6.1. Extend the round loop's `next_t` computation
to consult `input_event_queue[0][0]` alongside
`min_schedule_item.peek_time(default=Infinite)`. Drain
`handle_external_input_event` when `next_t == next_external` so the
event participates in the round.

**Validation** (must all pass after change):
- existing `pytest tests/test_hla_step.py` — 3 tests still pass
- new test in `test_hla_step.py`: an external event with timestamp
  `t` inside a grant fires at simulated time `t` (not at the next
  imminent's time)
- full `pytest tests/` — zero regressions in V_TIME, R_TIME, snapshot,
  hierarchical, structural, confluent, v_time_jump suites

**LOC**: ~10 LOC core change, ~30 LOC new test.
**Depends on**: PW.6 resolved (it is — option (a)).

### T4.1 — Confluent at imminent

**Files**: tests already written; verify or fix.
**Body**: M4.1. Counter imminent at t=0; inject inbound at t=0; expect
`con_trans` once.
**Validation**: `pytest -k test_M4_1` passes.
**Depends on**: T2.4 + (M4.0 if option (a)) + PW.4 (counter fixture).

### T4.2 — Non-imminent → ext_trans

**Body**: M4.2. As above with non-zero deadline; expect `ext_trans`.
**Validation**: `pytest -k test_M4_2`.
**Depends on**: T4.1.

### T4.3 — Two simultaneous inbound

**Body**: M4.3. Two ports, two events, same instant.
**Validation**: `pytest -k test_M4_3`.
**Depends on**: T4.2.

### T4.4 — Future-time inbound within grant

**Body**: M4.4. With PW.6 option (a) locked in, an event injected at
`t=2` with grant `5` must fire at simulated time `t=2`, not deferred.
**Validation**: `pytest -k test_M4_4`. Must pass after M4.0.
**Depends on**: T4.3 + M4.0.

### T4.5 — Beyond-grant deferral

**Body**: M4.5. Inject at t=10, grant 5 → no fire; next step(15) → fire.
**Validation**: `pytest -k test_M4_5`.
**Depends on**: T4.4.

---

## M5 — DEFERRED

Per PW.3, M5 is removed from the v1 plan. Re-evaluate after the v2
SnapshotExecutor work in pyjevsim core (out of scope here).

---

## Final integration tasks

### F.1 — Full-suite regression check

**Body**: `pytest tests/` (entire repo). Every existing test must
still pass — HLA work must not regress non-HLA behavior. Run after
each milestone closes; this is just the explicit "final check"
before shipping.

### F.2 — Coverage check

**Body**: `pytest --cov=pyjevsim/hla tests/hla/`. Line coverage of
the new package must be ≥95%. Anything uncovered must be justified
in writing.

### F.3 — Update `plan.md` milestone table

**Body**: mark each milestone's row as DONE with a date when its
tasks all close. Keep the table the source of truth for "what's
shipped."

### F.4 — Migrate `kdx-rti` adapter (downstream, separate repo)

Out of pyjevsim's repo. After F.1–F.3, `kdx-rti/python/kdx_rti/adapter.py`
collapses to a `Transport` implementation. ~400 LOC delete, ~150 LOC
of transport-only code remains. Tracked in kdx-rti issue, not here.

---

## Task dependency graph (TL;DR)

```
PW.1 PW.2 PW.3 PW.4 PW.5 PW.6 PW.7
   │
   ▼
T0.1 ─► T0.2 ─► T0.3 ─► T0.4 ─► T0.5
                                  │
                                  ▼
                                T1.1 ─► T1.2 ─► T1.3 ─► T1.4 ─► T1.5
                                                                  │
                                                                  ▼
                                                                T2.1 ─► T2.2 ─► T2.3 ─► T2.4
                                                                                          │
                                                                                          ▼
                                                                                        T3.1 ─► T3.2 ─► T3.3
                                                                                                          │
                                                                                  M4.0 ─────────────────► T4.1 ─► T4.2 ─► T4.3 ─► T4.4 ─► T4.5
                                                                                                                                            │
                                                                                                                                            ▼
                                                                                                                                          F.1 ─► F.2 ─► F.3
```

## Effort summary

| Block | Tasks                  | New code (LOC) | New tests (LOC) | Touches core? |
|-------|------------------------|----------------|------------------|----------------|
| PW    | PW.1 .. PW.7           | 0              | ~30 (fixtures)   | no             |
| M0    | T0.1 .. T0.5           | ~150           | ~80              | no             |
| M1    | T1.1 .. T1.5           | ~130           | (existing 11)    | no             |
| M2    | T2.1 .. T2.4           | ~55            | (existing 6)     | no             |
| M3    | T3.1 .. T3.3           | ~90            | (existing 9)     | no             |
| M4    | M4.0 + T4.1 .. T4.5    | ~10 (cond.)    | (existing 5)     | yes (cond.)    |
| F     | F.1 .. F.3             | 0              | 0                | no             |
| **Total** | **~25 tasks**       | **~435**       | **~30 + suite**  | **conditional**|

Each task fits a single agent session (≤1 hour focused). Pre-work fits
into a single session covering all of PW.1–PW.7 since they're all docs
+ a 10-line fixture change.
