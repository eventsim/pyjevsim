# pyjevsim HLA Subsystem — Development Plan

## Goal

Add IEEE 1516-2010 (HLA Evolved) federate support to pyjevsim **without
modifying `BehaviorModel`**. The feature lives at the `Executor` layer —
following the same decoration pattern as `SnapshotExecutor` — so existing
DEVS models become federates by configuration, not by inheritance.

## Architecture (one-line summary)

```
SysExecutor (already has ExecutionType.HLA_TIME + step(granted_time))
   └── HLAExecutor(BehaviorExecutor)   ← new; intercepts output(), routes inbound RTI events
        └── BehaviorModel              ← unchanged, pure DEVS
```

Lifecycle (`connect / join / publish / subscribe / resign / sync`) lives in
a separate `Federate` runtime helper, **not** in `HLAExecutor`. The grant
loop calls `SysExecutor.step(granted_time)` — already implemented at
`pyjevsim/system_executor.py:684`.

## Milestone breakdown

Each milestone is sized so a single agent can complete it in one session.
DONE = all tests for that milestone pass and earlier milestones still pass.
**For task-level breakdown of each milestone (T0.1, T0.2, ...) see
`docs/hla/tasks.md`.** Tasks are the unit of work an agent should pick up.

A pre-work block (PW.1–PW.7) addresses spec gaps found in plan review;
do PW before M0. See `docs/hla/tasks.md` § Pre-work.

| #  | Title                                  | Tasks         | New code (LOC) | Touches core? | Status |
|----|----------------------------------------|---------------|----------------|---------------|--------|
| PW | Spec / fixture corrections             | PW.1..PW.7    | 0 (docs only)  | no            | DONE 2026-05-07 |
| M0 | Foundation: bindings + transport + router | T0.1..T0.5 | ~120        | no            | DONE 2026-05-07 |
| M1 | `HLAExecutor` data path + wiring       | T1.1..T1.5    | ~95            | no            | DONE 2026-05-07 |
| M2 | `HLAExecutorFactory` + integration     | T2.1..T2.4    | ~30            | no            | DONE 2026-05-07 |
| M3 | `Federate` runtime + HLA_TIME loop     | T3.1..T3.3    | ~40            | no            | DONE 2026-05-07 |
| M4 | step() peek patch + confluent semantics | M4.0+T4.1..T4.5 | ~30 core | yes (step round loop) | DONE 2026-05-07 |
| M5 | Snapshot composition                   | DEFERRED v2   | -              | -             | DROP   |
| F  | Final integration                      | F.1..F.3      | 0              | no            | DONE 2026-05-07 |

**Final test count**: 86/86 pass — 40 pre-existing + 46 new HLA tests
(15 M0 + 11 M1 + 6 M2 + 9 M3 + 5 M4). Zero regressions.

After M5: subsystem is complete and usable against any `Transport`
implementation. Two transports follow as separate work items downstream
of pyjevsim:
- **D1** — gorti gRPC transport (lives in gorti repo, not pyjevsim).
- **D2** — kdx-rti ZMQ transport; `HLAAdapter` collapses into a transport
  implementation, the lifecycle/heartbeat/wake-port code goes away.

## Dependency graph

```
PW ──► M0 ──► M1 ──► M2 ──► M3 ──► M4 ──► F
```

M5 deferred. PW must close before any M-task starts.
For the task-level dependency graph (T0.1 → T0.2 → ...), see
`docs/hla/tasks.md` § Task dependency graph.

## TDD contract per milestone

1. Read the milestone's spec section (`docs/hla/specification.md`) and
   acceptance criteria (`docs/hla/qa.md`).
2. Run `pytest tests/hla/test_m<n>*.py` — every test starts skipped
   (the submodule under test does not exist yet).
3. Create the implementation module(s) listed under "Files" for that
   milestone. Tests un-skip and fail.
4. Make the failing tests pass **one at a time**. Do not move on while
   any test in the milestone is failing.
5. If a test still fails after **10 attempts**, stop and surface the
   problem to the user with: which test, what the assertion expects,
   what the code currently produces, and your hypothesis.
6. When all milestone tests pass, run the full pyjevsim suite
   (`pytest tests/`) — earlier milestones must still pass and no
   non-HLA tests may regress.
7. Commit with message `M<n>: <title>` and update this plan's table
   (mark DONE).

## What "simple and precise" means here

- One responsibility per class. `HLAExecutor` does data path. `Federate`
  does lifecycle. `Transport` does I/O.
- No backwards-compat shims. No "future-proofing" hooks. Add the next
  thing when the next milestone needs it.
- No comments restating what the code does. Comment only the *why*
  for non-obvious choices (e.g. "bound out-ports are RTI-only because
  mixing local + RTI fan-out caused ordering bugs in kdx-rti M5").
- Lift cleanly from `kdx-rti/python/kdx_rti/adapter.py` where its
  decisions were correct (correlation-id table, lifecycle order) and
  delete what it had to do because it was a `BehaviorModel` instead
  of an `Executor` (wake port, Idle/Draining/Ticking state machine).

## Out of scope

- Save / restore via the RTI's federation save service (M5 chooses the
  bypass option; cut-2 work).
- DDM regions, ownership management. Add when a transport demands them.
- Real-time pacing under HLA_TIME (HLA_TIME is logical-time only).
- Non-Python transports.

## File layout (final state at end of M5)

```
pyjevsim/hla/
  __init__.py              # public exports
  bindings.py              # HLAInteraction, HLAAttribute dataclasses (M0)
  transport.py             # Transport Protocol + LoopbackTransport (M0)
  hla_executor.py          # HLAExecutor (M1)
  factory.py               # HLAExecutorFactory (M2)
  federate.py              # Federate runtime (M3)

docs/hla/
  plan.md                  # this file
  specification.md         # contract / formal spec
  instruction.md           # developer guide
  qa.md                    # test plan + acceptance criteria

tests/hla/
  conftest.py              # shared fixtures: sample models, loopback wiring
  test_m0_foundation.py
  test_m1_data_path.py
  test_m2_factory.py
  test_m3_federate.py
  test_m4_confluent.py
  test_m5_snapshot.py
```
