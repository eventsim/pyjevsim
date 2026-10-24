# Changelog

All notable changes to pyjevsim are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.0] — UNRELEASED (date set at tagging)

### Highlights

2.3.0 is a performance and correctness release. The simulation engine is
faster on every measured interpreter, `import pyjevsim` no longer loads
`dill`, a replication runner (`pyjevsim.replication`) runs a model once per
seed on a process pool, and several snapshot, restore and signal-handling
defects are fixed. The HLA adapters are unchanged from 2.2.0. Code that
replaces executor methods at run time, keeps the message deliverer passed to
`output()`, or supplies a custom `ExecutorFactory` should read the Changed
section.

Performance. We compared the 2.3.0 release candidate's engine (`cba37cc`)
with 2.2.0 (`9a2b0d2`) using the standard suite (`benchmark/suite.py`, at
the revision in PR #51, which adds the Windows power-throttling opt-out).
The numbers below are 2.2.0 time divided by 2.3.0 time, from the minimum of
10 interleaved, parity-checked rounds, each run in a fresh process. W1 is
DEVStone HI 10x10, W2 DEVStone LI 10x10, W3 a sparse generator-to-sink
model, W4 an idle-heavy model (10,000 passive models), W5 the bank example,
and W7 W1 run through the `SnapshotExecutor` wrapper. On CPython 3.10.20,
2.3.0 is 1.6x faster on W1, W2 and W3, 1.4x on W4, 1.5x on W5 and 1.4x on
W7. On CPython 3.11.15: 1.9x on W1, 1.8x on W2, 1.9x on W3, 1.6x on W4,
1.5x on W5 and 1.6x on W7. On CPython 3.12.13: 1.9x on W1, 1.8x on W2,
1.9x on W3, 1.5x on W4, 1.6x on W5 and 1.6x on W7. On CPython 3.13.13:
2.4x on W1, 2.6x on W2, 2.2x on W3, 2.0x on W4, 1.7x on W5 and 2.1x on W7.
On CPython 3.14.0: 2.3x on W1, 2.5x on W2, 2.1x on W3, 1.9x on W4, 1.8x on
W5 and 2.0x on W7.

Most of the gain comes from the `SystemObject` counter fix (#41) and the
later engine work (#42, #44). Measured alone on W1, W3 and W5, #41 accounts
for about 30-50% of the gain on 3.10 and for more than half on 3.12 and
3.14, where 2.2.0 had become slower than on 3.12. For W7, the 2.2.0 side
used a compatibility shim for `SnapshotExecutor.con_trans`, so its ratio
also includes the #47 correctness change and is not a pure engine
comparison. Separately, `import pyjevsim` (W6) is about 4.5-7x faster on
every interpreter. This is mainly because 2.3.0 loads `dill` only when
snapshots are used, not because the engine changed.

Method and limits: all runs were on one Windows 11 desktop with an Intel
Core i7-12700 (20 logical CPUs, 64 GB RAM, no CPU pinning, Windows power
throttling turned off for the benchmark processes). The machine was shared
with other work and ran at about 20-35% background CPU load. The
interpreter builds differ (3.10-3.13 uv-managed, 3.14.0 from python.org),
so compare ratios across interpreters, not absolute times. We treat
differences under 5% as noise and do not report them, so read these
figures as approximate. An independent 5-round rerun of W1 and W5 on 3.10
and 3.14 agreed with them to within 3%. `cba37cc` is the engine as of
measurement, so changes made after it and before the 2.3.0 tag are not
covered. Linux and macOS were not measured. The full record is in
`benchmark/results/RELEASE-2.3.0-perf.md`, with the raw JSON in
`benchmark/results/release-2.3.0/`.

### Added
- A replication runner, `pyjevsim.replication` (SC-6).
  `run_replications(run, seeds, ...)` calls a picklable `run(seed)` once per
  seed on a persistent process pool (spawn by default) and returns the
  results in seed order. `ReplicationPool` reuses one pool across several
  batches, and `seed_sequence(base_seed, n)` derives distinct,
  platform-independent seeds. The runner sends seeds in chunks
  (`max(1, n // (4 * workers))` by default) and keeps two chunks per worker
  in flight. A batch with failing seeds raises one `ReplicationError` after
  all replications finish; it names every failing seed and keeps the
  successful results. A dead worker raises `BrokenReplicationPool` and a
  `timeout` raises `ReplicationTimeoutError`; both list the unfinished
  seeds. Options cover `progress`, an `initializer`, unordered results and
  `max_tasks_per_child` (Python 3.11+). A call made inside a worker runs
  sequentially, and `workers=0` runs in the calling process. Each
  replication gets its own seed, but a run is not yet bit-reproducible
  across processes. The guide, `docs/source/replication.rst`, covers usage
  and spawn rules and records the start-up cost and speed-ups measured on
  a shared machine. `examples/banksim/banksim_replications.py` compares
  sequential and pooled runs of the bank example.
- A standard performance suite, `python -m benchmark.suite`, with seven
  workloads: DEVStone HI and LI, a sparse generator, an idle-heavy model
  set, the bank example, import and start-up time, and DEVStone with every
  executor wrapped in `SnapshotExecutor`. Every timed run is a fresh
  process; base and candidate checkouts are interleaved round by round,
  compared by the ratio of minimums with a 5% noise floor, and refused
  when their transition counts or result counters differ. Optional CPU
  pinning, JSON and Markdown output. The workloads, measurement rules and
  an A/A noise floor are documented in `docs/source/benchmark.rst`.
- A call-count budget test (`tests/test_call_budget.py`) that counts the
  Python and C calls made per transition during `simulate()` and fails when
  either grows by more than 3% over the values recorded per Python version.
- The `SystemObject` class-attribute regression test now also checks that
  creating messages and models and running executors and the schedule
  queue never rebinds a class attribute of those hot-path classes.
- A behavioural trace oracle in `tools/oracle/`. It runs 18 scenarios
  (DEVStone, a 1000-model ring, the bank, HLA and mwmsim examples, and
  focused engine cases) against any checkout and reduces each to a sha256
  that ignores the order of same-time events. `tools/oracle/golden/v2.2.0.json`
  freezes v2.2.0. `tools/oracle/golden/v2.3.0-dev.json`, the golden CI
  compares with, differs from it only in `snapshot_restore`, which the
  snapshot fixes listed under Fixed change on purpose (recorded in
  `tools/oracle/LEDGER.md`). `order_check.py` reports whether the unsorted
  same-time order is reproducible across executor-hash salts.
- A CI job (`.github/workflows/oracle.yml`) that fails a pull request when a
  verdict scenario differs from the golden, or differs from the merge base
  without both an entry in `tools/oracle/LEDGER.md` and a new golden.
- `docs/source/semantics.rst`, describing the simulation semantics that
  models can currently observe, and a "Performance and semantics changes"
  section in `CONTRIBUTING.md`: performance-only and semantics-changing
  work go in separate pull requests, and every golden change is recorded
  in the ledger.
- A multi-event mode in the cross-engine DEVStone runner
  (`benchmark/run_compare.py`): `--events N` feeds N seed events into the
  root input at simulated times 0, P, 2P, ... (`--period P`), so every
  engine does exactly N times the single-seed transition work.
  `--events 1`, the default, keeps the single-seed path and its output
  layout. The 2026-10-22 comparison with xdevs.py, PythonPDEVS and the
  reference engine is recorded in `benchmark/results/COMPARE-2026-10-22.md`.
- The raw measurement records of the October 2026 performance work in
  `benchmark/evidence/2026-10/`.

### Changed
- `SysExecutor` calls a plain `BehaviorExecutor`'s model directly for
  output and transitions instead of going through the executor's
  forwarding wrappers, and skips the miss path for output ports with no
  coupling. Results and the same-time ordering rule are unchanged. As
  before, the order among models transitioning in the same instant follows
  set iteration (object identity), so it is not guaranteed to match
  between versions. The direct path is chosen when the executor is built:
  executors whose class overrides `output`/`int_trans`/`ext_trans`/
  `con_trans` (such as `HLAExecutor`), models whose class overrides
  `get_cancel_flag` or that have `get_cancel_flag` assigned on the
  instance before the executor is built, and `SnapshotExecutor`/
  `StructuralExecutor` keep the wrappers. Replacing those
  `BehaviorExecutor` methods on the class, or assigning them (or the
  model's `get_cancel_flag`) on an instance, after the executor is built
  is no longer seen; subclass it instead, or set `_model_fast = None` on
  the executor. The direct path also binds the model object when the
  executor is built: reassigning `executor.behavior_model` afterwards,
  including a `BehaviorExecutor` subclass that replaces it with a wrapper
  or proxy after `super().__init__()`, is not seen by output/transition
  dispatch (time advance and rescheduling do read the new model). Such
  code must also set `executor._model_fast`, to the new model or to `None`
  to use the wrappers. A `SysExecutor` subclass that overrides the private
  `_destinations_for` is no longer called for an uncoupled port when
  `track_uncaught` is off.
- The engine's per-instant loop does less fixed work: phase A reuses one
  `MessageDeliverer` for every imminent model in an instant (each model's
  messages still travel in their own list), phase B looks couplings up in
  `port_map` directly, phase D reschedules all affected models with one
  `ScheduleQueue.reschedule_all` call, and `schedule()` collects due models
  with `ScheduleQueue.pop_due`. Transition order and same-time semantics are
  unchanged. A model or `SnapshotCondition` that keeps a reference to the
  deliverer passed to `output()` (rather than to its contents) now sees later
  models' messages or an empty bag; keep `get_contents()` instead.
- `BehaviorExecutor` reschedules through a fused `_reschedule` method that
  does the work of `set_req_time` followed by `get_req_time`. Subclasses
  that override either method, directly or through a mixin, keep the
  two-call path automatically. Replacing `BehaviorExecutor.set_req_time` or
  `get_req_time` on the class at run time (monkeypatching,
  `mock.patch.object`) is not seen by the fused path. An executor returned
  by a custom `ExecutorFactory` must now derive from
  `pyjevsim.executor.Executor` (or provide `_reschedule`), in addition to the
  `_obj_id` and `_cached_destruct_time` attributes it already needed.
- `import pyjevsim` no longer imports `dill`, `json`, `ast` or `typing`; the
  snapshot and restore code imports them when it runs. Importing the package
  is about 5x faster. The incidental module attributes
  `pyjevsim.snapshot_manager.dump`/`json`,
  `pyjevsim.restore_handler.load`/`loads`/`json`/`ast`,
  `pyjevsim.snapshot_executor.dill`, `pyjevsim.system_executor.copy`/`math`
  and `pyjevsim.structural_executor.copy`/`heapq` are gone, and importing
  pyjevsim no longer triggers dill's import-time registration in the
  pure-Python pickler.
- `SysMessage` no longer calls `SystemObject.__init__`: it takes its ID from
  the same shared counter directly, so IDs, ordering and the pickled
  instance state are unchanged. Building a message is about 1.4x faster on
  CPython 3.14. Code that wraps or monkeypatches `SystemObject.__init__`
  (for example to count created objects) no longer sees messages.
- Examples: the bank example (`examples/banksim`) can be seeded. The
  `banksim_*.py` scripts take `--seed N` (or an optional `seed` key in
  `scenario.yaml`), plus `--max-user` and `--config`. A seeded run gives
  every generator its own `random.Random` derived from the seed and the
  generator's name (`examples/banksim/seeding.py`) and uses
  `OrderedBankQueue`/`OrderedBankResult`, which apply the messages of an
  instant in a fixed order, so the same seed gives a byte-identical report
  in every process. Without a seed nothing changes: the models draw from
  the module-level `random` and the scripts use `BankQueue`/`BankResult`;
  `BankUserGenerator(name, rng=None)` and `Banksim(name, seed=None)` keep
  their defaults. The examples README lists which variants are the same
  simulation.
- Examples: the bank what-if change is applied by one function
  (`examples/banksim/runner.py`) in `banksim_classic.py` and
  `banksim_restore.py`. Fewer generators: `gen{wiq_gen_num}` ...
  `gen{gen_num-1}` are stopped through their new `stop` port (before, the
  scripts idled `wiq_gen_num` generators, different ones in each script,
  and each still emitted the user it had scheduled). More generators: the
  added ones are named `gen{gen_num}` ... and started on their own port
  (before, `banksim_classic.py` named them `gen0` ... again, and both
  scripts restarted every running generator once per added one).
- Examples: the bank result report is written in chunks and flushed once
  before `os._exit(0)`, instead of one flushed `print` per line; the text
  is the same. For 500000 served and about as many dropped customers with
  output to a file this takes 0.7 s instead of 19-38 s.
- Examples: mwmsim's `Statistic` seeds its stream from its `seed` argument
  and its creation index (`core_component.stream_seed`) instead of the
  wall clock, so a scenario with the same `RANDOM_SEED` repeats exactly;
  `job.py` and `check.py` pass `RANDOM_SEED` where they passed `0`. The
  trace oracle's `mwmsim_433sbh` scenario pins the seeds through
  `stream_seed` to the values its fake clock gave before; its hash is
  unchanged.
- `SysExecutor.simulate()` registers its executor through the new
  `TerminationManager.attach()` instead of building a `TerminationManager`
  on every call, and no longer sets the unused `SysExecutor.tm` attribute.
  Registration stays weak and idempotent, and the handlers are still
  reinstalled when something has reset them. The replication guide, the
  runner docstring and `banksim_replications.py` no longer describe the
  registry leak that was fixed earlier in this release; they recommend
  `simulate(..., _tm=False)` inside a replication because the handler
  would turn a Ctrl+C into silently truncated results.

### Fixed
- `SystemObject` no longer rebinds a class attribute on every instantiation.
  The former global ID counter (`SystemObject.__GLOBAL_OBJECT_ID += 1`)
  invalidated the type version of every model, executor and message class
  on each object creation, which exhausted CPython's per-type version cap
  early in a run and left attribute access unspecialised for the rest of the
  process (CPython 3.11 and later). IDs now come from a shared
  `itertools.count`; they stay unique and increasing, so ordering is
  unchanged. On CPython 3.14 the DEVStone HI benchmark runs about 1.8x
  faster and the bank example about 1.4x faster.
- The dill requirement now follows the Python version. `dill>=0.3.6`
  allowed releases that predate support for the Python in use (0.3.6
  was released before Python 3.12 existed); the minimum is now the
  first release with formal support for that Python: 0.3.6 on 3.10,
  0.3.7 on 3.11, 0.3.8 on 3.12, 0.3.9 on 3.13 and 0.4.1 on 3.14. A CI
  job runs the snapshot and restore tests against exactly these
  versions, and the test matrix now includes Windows and Python 3.14.
- A model registered with a `SnapshotCondition` no longer raises
  `AttributeError` when it is imminent and receiving input at the same
  instant: `SnapshotExecutor` now has `con_trans`. The condition's
  internal-transition hooks (`snapshot_pre_condition_int`/
  `snapshot_post_condition_int`) run before and after the whole confluent
  transition, and their snapshots are written as `[int_before]`/
  `[int_after]`; the external-transition hooks are not called for the
  messages consumed by a confluent transition.
- `SnapshotExecutor.output` calls `snapshot_post_condition_out(msg, cur_state)`
  in the argument order that `SnapshotCondition` declares. It used to pass
  `(cur_state, msg)`; a condition written against the base-class signature
  received the two swapped (harmless while `cur_state` was always `""`).
- `SnapshotCondition` hooks receive the model's current state as
  `cur_state`. They used to receive `""` every time, because
  `BehaviorExecutor.get_cur_state()` returned a field of the executor that
  was never updated; it now returns the model's state, and
  `BehaviorExecutor.init_state()` sets it on the model.
- `SysExecutor.simulate()` no longer reinstalls the SIGINT/SIGTERM handlers
  on every call, and no longer keeps every executor it has run alive for
  the rest of the process. `TerminationManager` installs its handlers from
  the main thread only when they are not already in place, and holds
  executors in a `WeakSet`. If something resets SIGINT or SIGTERM between
  runs (ipykernel restores `default_int_handler` before every cell), the
  next main-thread `simulate()` installs the handler again, as before.
  `simulate()` on a worker thread no longer raises `ValueError` from
  `signal.signal`; its executor is still terminated by a signal once the
  main thread has installed the handlers (any `simulate()` or
  `TerminationManager()` on the main thread does).
- Models created after restoring a simulation snapshot in a new process no
  longer reuse the object IDs of restored models. `SysExecutor` keys its
  active models by object ID, so such a collision silently dropped one of
  the two executors (the restored engine's own `dc` catcher already
  collided with the restored `dc`). `snapshot_simulation` now records the
  next free ID as `next_object_id` in `model_map.json`, and
  `RestoreHandler` moves the ID counter past it, or past the highest
  restored model ID for snapshots saved without it, before it builds the
  executor. `RestoreHandler` therefore creates its `SysExecutor` in
  `get_engine()`/`restore_engine()` instead of in its constructor
  (`RestoreHandler.engine` is `None` until then), and each `get_engine()`
  call builds a new executor instead of registering the models again in
  the same one.
- `SysExecutor.register_entity` raises `ValueError` when a model with the
  same object ID is already registered and not destroyed (the same model
  registered twice, or two `copy.deepcopy`/`dill` copies of one model),
  instead of replacing the first model's executor.
- `RestoreHandler.load_snapshot` (and `SnapshotManager.load_snapshot`) gives
  the loaded model a new object ID, so one model snapshot can be loaded and
  registered several times, as the BankSim what-if example does.
- Examples: `banksim_classic.py` tested the loop variable `i` left over from
  building the models, so its what-if change never happened (or happened on
  every step when `wiq_time` was `proc_num - 1`). It now counts `simulate(1)`
  steps and applies the change once, after `wiq_time` steps, where
  `banksim_snapshot.py` takes its snapshot.
- Examples: `BankUserGenerator` declares the `stop` input port it handled,
  and its handler sets `_cur_state` instead of the misspelt `_cur_satate`,
  so a generator can be stopped.
- Examples: `banksim_model_snapshot.py` registered every generator twice,
  which `register_entity` now rejects with `ValueError` at start-up.

## [2.2.0] — 2026-08-29

### Added
- Open-source Portico 2.1.4 backend for the IEEE 1516-2010 Java API, including
  a standard-layout `HLAunicodeString` codec and receive-order tick buffering.
- Experimental native-Python GORTI adapter for interactions, object
  registration/discovery and attribute update/reflection, and
  regulating/constrained logical-time paths. It requires GORTI's
  source-installed `rti1516e` SDK and a separately built `rtid`.
- Two-federate AT/SIM example with self-propelled and stationary decoy
  scenarios, committed 180-row references, and offline and live comparison
  commands.
- Portico versions of the ping-pong and AT/SIM examples, plus a same-JVM RID
  used by the bundled Portico runs.
- GORTI AT/SIM runner and live-verifier selection, including optional managed
  `rtid` startup and isolated temporary save/state directories.
- HLA architecture, service coverage, time-management notes, limitations,
  related work, expected traces, and reproduction instructions under
  `docs/hla-validation/`.
- CI checks for the Java-free equivalence run and committed result files.
- CI checks that build the Sphinx documentation with warnings as errors and
  validate both distribution artifacts with Twine.
- `hla-java` dependency extra for the Java-backed Pitch and Portico adapters;
  `hla-pitch` remains available for compatibility.
- Runtime validation for binding directions and publish/subscribe direction
  guards, with regression tests.

### Changed
- Build metadata now requires setuptools 77 or newer and declares the MIT
  license file using PEP 639 fields.
- `PitchTransport` now provides `_encode_value`, `_decode_value`, `_rti_time`,
  and `_rti_lookahead` extension hooks used by the Portico adapter.
- The live AT/SIM verifier fails when the expected peer reflection is missing,
  a worker exits with an error, or a scenario exceeds the configured watchdog
  period.
- `InProcessRTI` capability metadata no longer advertises HLA time management or
  timestamp-order delivery. It is an identity-grant test bus; example drivers
  coordinate lock-step explicitly.

### Known limitations
- GORTI support is experimental and excluded from release-grade, complete HLA
  Object Management, and formal IEEE 1516 conformance claims.

## [2.1.2] — 2026-06-28

### Added
- Distributed (multi-process) HLA ping-pong example: each federate runs as
  its own OS process (own JVM/LRC) joined to one Pitch pRTI federation
  (`examples/hla_pingpong/run_pitch_federate.py`,
  `run_pitch_multiprocess.py`). Federates share a start barrier via a
  federation synchronization point.
- `PitchTransport`: federation synchronization-point support
  (`register_sync_point` / `wait_sync_announced` / `achieve_sync_point` /
  `wait_synchronized`) and a configurable CRC endpoint
  (`crc="host:port"`, also via `PYJEVSIM_CRC`) for selecting a local or remote
  CRC address.
- Packaging/citation: `.zenodo.json` and `CITATION.cff` for an archival
  DOI; Zenodo DOI badge in the README.

## [2.1.1] — 2026-06-28

### Fixed
- Republish from ``main``. The PyPI **2.1.0** artifact was built from the
  feature branch before it was reconciled with ``main`` and shipped an
  older ``HLAExecutor`` inbound convention (whole-list
  ``insert_external_event``) that differed from the tagged ``main`` source
  (per-item injection). PyPI versions are immutable, so 2.1.0 cannot be
  replaced; 2.1.1 is the canonical build from ``main`` (the in-tree
  behaviour and tests are unchanged from the 2.1.0 source on ``main``).

## [2.1.0] — 2026-06-28

### Added
- Pluggable HLA connector interface so backends other than the test loopback can be
  plugged in:
  - `RTIConnector` template-method base class (`pyjevsim/hla/transport.py`) —
    `_do_send` / `_do_request_time_advance` form the minimum abstract surface;
    live HLA adapters also supply lifecycle, declaration, and receive hooks;
    direction enforcement, codec calls,
    single-callback dispatch, the join/resign state machine and idempotent
    close are inherited.
  - `RTICapabilities` (feature negotiation), `Codec` / `IdentityCodec`
    (FOM encoding decoupled from transport), and a name→factory registry
    (`register_rti` / `create_rti` / `available_rtis`).
  - `docs/hla/rti_interface.md` documenting how to add a backend.
- RTI backends under `pyjevsim/hla/backends/`:
  - `InProcessRTI` — multi-federate in-process bus (no Java) for tests/demos.
  - `PitchTransport` — IEEE 1516-2010 backend for **Pitch pRTI** via JPype.
    Verified live against Pitch pRTI Free 5.5.2 with Temurin 11.
- `examples/hla_pingpong/` — two-federate (ping/pong) example demonstrating
  federation join/resign, interaction exchange, and object-attribute
  synchronization. Runs offline (`run_inprocess.py`) or against a live CRC
  (`run_pitch.py`); FOM in `fom/PingPong.xml`.
- Tests: `tests/hla/test_rti_interface.py`, `tests/hla/test_pingpong.py`
  (always run), `tests/hla/test_pitch_backend.py` (guarded; live when
  `PYJEVSIM_JVM` + `PYJEVSIM_PITCH_LIVE` + a running CRC are present).
- `hla-pitch` optional dependency extra (`jpype1`).

### Changed
- `SysExecutor.schedule` (V_TIME/R_TIME) and `SysExecutor.step` (HLA_TIME) now
  share the two-phase `SysExecutor._run_instant` transition path.

### Fixed
- External events on the V_TIME/R_TIME path were delivered by a legacy
  pre-pass (`handle_external_input_event` → `single_output_handling`) that ran
  `ext_trans` *before* imminent models computed `output()` and could never
  produce `con_trans`. They now flow through the shared two-phase tick: a model
  that is both imminent and externally influenced at one instant invokes
  `con_trans` (TSO/confluent), matching the HLA `step` path. The legacy methods
  are retained (deprecated) for backward compatibility; a latent `msg[1]` indexing
  bug in `single_output_handling` is fixed.

## [2.0.1] — 2026-05-06

### Changed
- Documentation overhaul: `README.md` now ships PyPI/RTD/license badges,
  PyPI install instructions, and a runnable generator → sink quick start.
- Sphinx docs updated for 2.0: "What's new in 2.0" landing section,
  HLA `step()` and two-phase tick subsections in the quick start,
  autodoc coverage for `atomic_model`, `schedule_queue`, and
  `message_deliverer`. Author / release metadata in `conf.py` set to
  `Changbeom Choi` and `2.0.0`.
- `StructuralModel` gains class- and method-level docstrings.
- `SysExecutor` class docstring expanded to describe the two-phase
  tick and the three execution modes; `ex_mode` argument now documents
  `HLA_TIME`.

### Fixed
- Quick-start `output()` example used the legacy `return msg` pattern
  that the v2.0 two-phase tick silently ignores. Updated to call
  `msg_deliver.insert_message(msg)`.
- Typo in `behavior_model` module docstring ("BehaivorModel").

## [2.0.0] — 2026-05-06

### Added
- DEVStone benchmark suite under `benchmark/` with LI/HI/HO topology builders,
  parameterizable atomic, and a CLI runner (`run_devstone.py`) for single
  configs and sweeps with CSV output (commit `80fa704`).
- Cross-engine comparison harness: `benchmark/engines/` with adapters for
  `pyjevsim`, `pypdevs`, `xdevs`, and a `reference` engine, driven by
  `run_compare.py` and `run_sparse.py`; historical summaries recorded in
  `benchmark/results/{BASELINE,SPARSE,ALIASING}.md`.
- New tests:
  - `tests/test_confluent.py` — Parallel-DEVS confluent-transition semantics
    for the two-phase tick.
  - `tests/test_hla_step.py` — `SysExecutor.step(granted_time)` contract for
    HLA federate ambassadors driving pyjevsim under an IEEE 1516-2010 RTI.
  - `tests/test_v_time_jump.py` — V_TIME scheduler hops to the next event
    instead of advancing by a fixed `time_resolution`.
  - `tests/test_track_uncaught.py` — opt-in `track_uncaught` flag routes
    messages on uncoupled ports to `DefaultMessageCatcher`.
- Benchmark usage documented in `docs/source/benchmark.rst`.

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
  `get_next_event_time()` for federate-driven time advancement.
- Pause/resume API on `SysExecutor` backed by `threading.Condition`.
- Thread safety for external event insertion and graceful shutdown.
- PyPI packaging via `pyproject.toml` and `MANIFEST.in`; minimum Python
  raised to 3.10.
- `exgen.py` example generator; banksim test suite.

### Changed
- `ScheduleQueue` switched from `deque` + `sorted()` to `heapq`.
- `waiting_obj_map` lookup and external input handling optimized.
- `TerminationManager` now performs a graceful shutdown instead of
  calling `os._exit(0)`.
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

[Unreleased]: https://github.com/eventsim/pyjevsim/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/eventsim/pyjevsim/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/eventsim/pyjevsim/compare/v2.1.2...v2.2.0
[2.1.2]: https://github.com/eventsim/pyjevsim/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/eventsim/pyjevsim/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/eventsim/pyjevsim/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/eventsim/pyjevsim/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/eventsim/pyjevsim/compare/v1.3.1...v2.0.0
[1.3.1]: https://github.com/eventsim/pyjevsim/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/eventsim/pyjevsim/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/eventsim/pyjevsim/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/eventsim/pyjevsim/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/eventsim/pyjevsim/releases/tag/v1.0.0
