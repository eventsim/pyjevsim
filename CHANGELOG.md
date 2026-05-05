# Changelog

All notable changes to pyjevsim are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] — 2026-05-06

### Added
- DEVStone benchmark suite under `benchmark/` with LI/HI/HO topology builders,
  parameterizable atomic, and a CLI runner (`run_devstone.py`) for single
  configs and sweeps with CSV output (commit `80fa704`).
- Cross-engine comparison harness: `benchmark/engines/` with adapters for
  `pyjevsim`, `pypdevs`, `xdevs`, and a `reference` engine, driven by
  `run_compare.py` and `run_sparse.py`; results recorded in
  `benchmark/results/{BASELINE,SPARSE,ALIASING}.md` and matching CSVs.
- New tests:
  - `tests/test_confluent.py` — Parallel-DEVS confluent-transition semantics
    for the two-phase tick.
  - `tests/test_hla_step.py` — `SysExecutor.step(granted_time)` contract for
    HLA federate ambassadors driving pyjevsim under an IEEE 1516-2010 RTI.
  - `tests/test_v_time_jump.py` — V_TIME scheduler hops to the next event
    instead of advancing by a fixed `time_resolution`.
  - `tests/test_track_uncaught.py` — opt-in `track_uncaught` flag routes
    messages on uncoupled ports to `DefaultMessageCatcher`.
- Documentation: `docs/source/benchmark.rst`, `docs/cascade_scheduling_proposal.md`,
  `docs/t1_2_scheduler_analysis.md`, `docs/p_plan.md`.

### Changed
- `SysExecutor` rewritten around a two-phase tick (output → confluent/ext/int
  transitions) instead of interleaving each model's output, receivers'
  `ext_trans`, and own `int_trans` inside one inner loop — fixes
  confluent-event ordering.
- V_TIME schedule loop now jumps to the next scheduled event time rather
  than advancing by `time_resolution`.
- `ScheduleQueue`, `MessageDeliverer`, `BehaviorExecutor`, and
  `StructuralExecutor` updated to support the new tick and HLA `step()` path.
- README and Sphinx quick-start / examples pages updated for the new APIs.

## [1.3.1] — 2026-04-12

### Changed
- `dill` promoted from optional to a required runtime dependency.
- Removed legacy `setup.py`; packaging is driven entirely by `pyproject.toml`.
- Version bumped to 1.3.1.

## [1.3.0] — 2026-03-20

### Added
- HLA support: `HLA_TIME` execution mode plus `SysExecutor.step()` and
  `get_next_event_time()` for federate-driven time advancement
  (S1+S2+S3, S6).
- Pause/resume API on `SysExecutor` backed by `threading.Condition`
  (M1+M2+M3).
- Thread safety for external event insertion and graceful shutdown
  (M4+M5+M6+M7+S4, S5).
- PyPI packaging via `pyproject.toml` and `MANIFEST.in`; minimum Python
  raised to 3.10.
- `exgen.py` example generator; banksim test suite.

### Changed
- `ScheduleQueue` switched from `deque` + `sorted()` to `heapq` (P1).
- `waiting_obj_map` lookup and external input handling optimized
  (P2+P3).
- `TerminationManager` now performs a graceful shutdown instead of
  calling `os._exit(0)` (S5).
- README updated for the new APIs and execution modes.

### Fixed
- `BehaviorModel` `global_time` initialization in test models.
- R_TIME elapsed-time calculation (operand order was reversed).
- Termination condition compared a string against the `ExecutionType`
  enum.

## [1.2.0] — 2025-05-16

### Added
- Anti-Torpedo simulator example, including self-propelled and
  stationary decoy models and scenario YAMLs.
- Municipal Waste Management simulator example.
- Snapshot/restore updates to the simulation engine and snapshot
  executor; `ObjectDB` updates supporting them.
- Read the Docs documentation pass.

### Changed
- Banksim example refreshed; example directory structure reorganized.

## [1.1.0] — 2025-03-16

### Added
- Classical DEVS support with explicit Atomic and Coupled models, plus
  a Classical-DEVS test case.
- Structural-model improvements landed via the `feature/structural_model`
  branch.
- `test_adev` example added.

## [1.0.0] — 2024-11-04

- Initial public release: DEVS modeling & simulation framework with
  journaling (snapshot/restore), `BehaviorModel` / `StructuralModel`,
  `SysExecutor` with V_TIME and R_TIME execution modes, port-based
  coupling, and `dill`-backed serialization.

[Unreleased]: https://github.com/eventsim/pyjevsim/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/eventsim/pyjevsim/compare/v1.3.1...v2.0.0
[1.3.1]: https://github.com/eventsim/pyjevsim/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/eventsim/pyjevsim/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/eventsim/pyjevsim/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/eventsim/pyjevsim/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/eventsim/pyjevsim/releases/tag/v1.0.0
