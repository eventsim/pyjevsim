# pyjevsim HLA Subsystem — QA / Test Plan

The test suite under `tests/hla/` encodes the specification in
`docs/hla/specification.md`. Each milestone has one test file. Tests
**skip** until their target submodule is importable; once imported they
run and must pass before that milestone is considered DONE.

## Skip-until-importable contract

Each test file begins with:

```python
import pytest
pytest.importorskip("pyjevsim.hla.<submodule>")
```

The agent working a milestone:
1. Runs `pytest tests/hla/test_m<n>*.py -v`. Initially all tests skip.
2. Creates the submodule (empty stub is enough to un-skip).
3. Re-runs. Tests now fail with concrete assertions.
4. Implements until tests pass.
5. Runs the full suite and confirms no regressions in `tests/`.

## Acceptance criteria by milestone

### M0 — Foundation (`test_m0_foundation.py`)

| ID    | Acceptance criterion                                                     |
|-------|--------------------------------------------------------------------------|
| M0.1  | `HLAInteraction` and `HLAAttribute` are frozen, hashable, equal by value |
| M0.2  | `HLAInteraction(fom_id="X")` defaults to `direction="out"`, `kind="interaction"` |
| M0.3  | `HLAAttribute(fom_id="X", object_class="Y")` works; `kind="attribute"`   |
| M0.4  | `Transport` Protocol has the four required methods                       |
| M0.5  | `LoopbackTransport.send` invokes `on_receive` with mirrored binding      |
| M0.6  | `LoopbackTransport.send` does nothing if no callback registered          |
| M0.7  | `LoopbackTransport.request_time_advance(t)` returns `t` unchanged        |
| M0.8  | `LoopbackTransport.close()` is idempotent                                |

### M1 — Data path (`test_m1_data_path.py`)

| ID    | Acceptance criterion                                                     |
|-------|--------------------------------------------------------------------------|
| M1.1  | `HLAExecutor` is a subclass of `BehaviorExecutor`                        |
| M1.2  | Constructor stores `transport`, `bindings`, `sys_executor`               |
| M1.3  | Constructor with binding referencing unknown port raises `ValueError`    |
| M1.4  | Output on a bound `out` port goes to `transport.send`, not `msg_deliver` |
| M1.5  | Output on an unbound port flows through `msg_deliver` normally           |
| M1.6  | Output on a bound `inout` port goes to transport (out-side wins)         |
| M1.7  | `_on_rti_event` for a subscribed `(kind, fom_id)` calls `insert_external_event` |
| M1.8  | `_on_rti_event` for a non-subscribed `(kind, fom_id)` is a no-op         |
| M1.9  | `_on_rti_event` with timestamp in the past clamps `delay` to 0           |
| M1.10 | Empty bindings ⇒ behaves identically to `BehaviorExecutor` (no transport calls) |
| M1.11 | Transport `send` exception propagates out of `output()`                  |

### M2 — Factory (`test_m2_factory.py`)

| ID    | Acceptance criterion                                                     |
|-------|--------------------------------------------------------------------------|
| M2.1  | `HLAExecutorFactory` is a subclass of `ExecutorFactory`                  |
| M2.2  | Model with bindings ⇒ factory returns `HLAExecutor`                      |
| M2.3  | Model without bindings ⇒ factory returns plain `BehaviorExecutor`        |
| M2.4  | Assigning factory to `sys_exec.exec_factory` and registering a model produces the right executor |
| M2.5  | `register_entity` followed by an `HLA_TIME` `step()` round delivers a bound output to the transport |
| M2.6  | Two models cross-wired via `LoopbackTransport` exchange messages end-to-end |

### M3 — Federate runtime (`test_m3_federate.py`)

| ID    | Acceptance criterion                                                     |
|-------|--------------------------------------------------------------------------|
| M3.1  | `Federate(sys_exec, transport)` constructs without I/O                   |
| M3.2  | `publish(binding)` before `join` raises `RuntimeError`                   |
| M3.3  | `subscribe(binding)` before `join` raises `RuntimeError`                 |
| M3.4  | `join → publish → subscribe → resign` sequence does not raise            |
| M3.5  | `run_until(end_time=10, lookahead=1)` calls `request_time_advance` ≥10 times |
| M3.6  | `run_until` calls `sys_exec.step(granted)` for each grant                |
| M3.7  | `run_until` exits when `global_time ≥ end_time` even if granted < target |
| M3.8  | `lookahead <= 0` raises `ValueError`                                     |
| M3.9  | When transport grants `min(target, capped)`, `run_until` advances correctly |

### M4 — Confluent semantics (`test_m4_confluent.py`)

Prerequisite: **M4.0** — `SysExecutor.step` round-loop patch
(specification.md §6.1) lands before any M4 test runs. Verify
`pytest tests/test_hla_step.py` and the full `tests/` suite still pass
after the patch.

| ID    | Acceptance criterion                                                     |
|-------|--------------------------------------------------------------------------|
| M4.1  | RTI event injected at time `t` while model is imminent at `t` ⇒ `con_trans` fires once |
| M4.2  | RTI event injected at time `t` while model is non-imminent ⇒ `ext_trans` fires once |
| M4.3  | Two RTI events at the same time on different ports of the same model ⇒ both delivered before next round |
| M4.4  | RTI event injected with `t` inside the grant window ⇒ fires at simulated time `t` during this step (requires M4.0) |
| M4.5  | RTI event injected with timestamp beyond the grant ⇒ deferred to the next step |

### M5 — DEFERRED to v2

Removed from the v1 plan. `SnapshotExecutor` integration requires a
core hook that is not worth adding in v1; HLA federates are not
snapshot-able under this plan. See `docs/hla/specification.md §7`.

## Test execution discipline

- **One milestone at a time.** Do not run M2 tests while M1 tests fail.
- **No mutation in a fixture.** Fixtures must be re-entrant. Use
  `pytest.fixture(scope="function")` (the default) for everything HLA-related.
- **No real network or threads in unit tests.** `LoopbackTransport` is
  in-process and synchronous (or uses a single deterministic worker
  thread that the test starts and stops explicitly).
- **Assertions cite the spec section.** When a test fails, the message
  should make it obvious which spec rule is violated. Prefer
  `assert actual == expected, f"§3.2: bound out port must not reach msg_deliver"`
  over a bare `assert`.
- **Coverage gate.** When all M0–M5 tests pass, run
  `pytest --cov=pyjevsim/hla tests/hla/` — line coverage of `pyjevsim/hla/`
  must be ≥95%. Anything uncovered must have a written reason in the
  PR description.

## Failure protocol

If a test fails after **10 attempts** to make it pass, stop. Surface to
the user:
1. The test ID (e.g. M1.7).
2. The exact assertion / exception.
3. The current implementation behavior.
4. Two or three plausible root-cause hypotheses, ranked.
5. The smallest reproducer you have.

Do not bypass the test by weakening the assertion or by `xfail`-marking
it. The test exists because the spec demands it; weakening the test
weakens the contract.

## Regression safety net

Before any milestone is closed, run the full suite:

```bash
pytest tests/                # all of pyjevsim, including non-HLA tests
```

The HLA work must not regress any existing test. If it does, the change
is wrong — the existing behavior is the reference.
