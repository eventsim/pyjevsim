# pyjevsim Performance Enhancement Plan

This document catalogues performance opportunities identified by reading the
current codebase and running the DEVStone benchmark under `benchmark/`. Each
item has concrete file:line anchors, a rationale, an expected impact band, and
a rough complexity estimate so the work can be prioritised.

Baseline — captured 2026-05-05 with `python3 -m benchmark.run_compare`,
single seed event, no synthetic CPU work, best of three runs. Full numbers
live in [`../benchmark/results/BASELINE.md`](../benchmark/results/BASELINE.md):

| variant | d × w | pyjevsim tr/s | xdevs tr/s | pypdevs tr/s | reference tr/s |
|---------|-------|---------------|------------|--------------|----------------|
| LI      | 4 × 4 |   175 k       |   689 k    |   765 k      | 1.68 M         |
| LI      | 6 × 6 |   137 k       |   960 k    |  1.10 M      | 2.18 M         |
| HI      | 4 × 4 |   233 k       |   546 k    |   888 k      | 2.00 M         |
| HI      | 6 × 6 |   203 k       |   664 k    |  1.37 M      | 2.35 M         |
| HO      | 4 × 4 |   241 k       |   757 k    |   918 k      | 1.97 M         |
| HO      | 6 × 6 |   198 k       |   810 k    |  1.38 M      | 2.34 M         |

Geometric-mean slowdown of pyjevsim against the comparison set:

- vs **xdevs**: ~3.7×
- vs **pypdevs (minimal kernel)**: ~5.0×
- vs **reference floor**: ~10×

The hand-rolled reference engine in `benchmark/engines/reference/` is the
ceiling on what the optimisations below can realistically buy. xdevs and
pypdevs are the closest peers — items are ordered to close that gap first.

---

## Tier 1 — high-leverage, low-risk

### T1.1  Skip-to-next-event scheduling in V_TIME mode  ✅ Landed

**Status.** Implemented. `SysExecutor.schedule()` now jumps `global_time`
directly to the next scheduled event in V_TIME mode (FEL head, external
input queue head, or waiting-creation queue head — whichever is smallest,
clamped at `target_time`). R_TIME still steps by `time_resolution` and
HLA_TIME is unchanged. Helper added: `_peek_next_event_time()`. Tests live
in `tests/test_v_time_jump.py` (5 tests covering correctness of fire times,
non-integer time advances, horizon clipping, and a wall-time budget).

**Realised impact** (`benchmark/results/SPARSE.md`):

| period | pyjevsim before | pyjevsim after | speedup |
|--------|-----------------|----------------|---------|
| 1      |    264 k tr/s   |    279 k tr/s  |   ~1×   |
| 10     |     74 k tr/s   |    282 k tr/s  |  3.8×   |
| 100    |      9 k tr/s   |    285 k tr/s  |   31×   |
| 1000   |      1 k tr/s   |    290 k tr/s  |  263×   |

pyjevsim is now period-independent like xdevs / pypdevs / reference. The
dense-DEVStone baseline is unchanged because every transition there lives
at the same simulated instant — that gap is now T1.2's responsibility.

### Cascade-aware two-phase tick — ✅ Landed

**Status.** Implemented as the bug fix for the confluent-transition
quirk noted in earlier baselines. `SysExecutor.schedule()`
(`pyjevsim/system_executor.py`) now executes the four-phase Parallel
DEVS schedule (Phase A pop imminents → Phase B route λ outputs → Phase
C apply `δ_int`/`δ_ext`/`δ_con` → Phase D bulk reschedule). New
`con_trans` method on `BehaviorModel` / `BehaviorExecutor` /
`StructuralExecutor` with default `δ_int; δ_ext`. New `_in_heap` set on
`SysExecutor` to bound heap growth; `heapify` now runs once per tick.
4 new tests in `tests/test_confluent.py`; full suite now 34/34 passing.

**Behaviour change.** HI / HO transition counts now match xdevs /
pypdevs / reference (38 / 152 instead of pyjevsim's previous 26 / 72
for d4w4 / d6w6). Existing models without confluent cases inherit the
default `con_trans` and behave identically. See
`docs/cascade_scheduling_proposal.md` for the design rationale and the
migration plan that called this out as a deliberate semantics
correction.

### Sparse-time per-tick overhead reductions — ✅ Landed

In sparse-time workloads `schedule()` runs ~100× per simulated run (one
call per event), each with only 2 transitions worth of actual work, so
per-tick fixed cost dominated. Four cheap fixes:

1. **`handle_external_input_event` early returns** when
   ``input_event_queue`` is empty. Skips the lock and the
   ``MessageDeliverer`` allocation that ran every tick even with no
   external producer.

2. **`destroy_active_entity` skips its full scan** when no registered
   executor has a finite ``destruct_time``. Tracks a
   ``_destructs_pending`` counter; the scan only runs when it is
   non-zero. Switches the inner check from ``get_destruct_time()``
   (method dispatch) to ``_cached_destruct_time`` (direct attr read).
   Added ``_cached_destruct_time`` to ``StructuralExecutor`` to match.

3. **`_peek_next_event_time` open-coded.** Old version built a
   ``candidates`` list and called ``min(...)`` even with one entry.
   New version short-circuits — typical sparse case is a single
   ``peek_time`` call followed by two cheap ``if`` branches.

4. **`simulate()` skips the all-passive peek** unless the user passed
   an unbounded horizon. For finite ``simulate(_time)`` the loop
   already exits when ``global_time`` reaches ``target_time`` via the
   Phase E jump-step; the redundant ``peek_time`` per loop iteration
   was pure overhead.

**Realised impact on sparse-time** (100 events, varying period):

| period | before | after | speedup |
|--------|------:|------:|--------:|
| 1      | 332 k | 393 k | 1.18×   |
| 10     | 334 k | 410 k | 1.23×   |
| 100    | 345 k | 412 k | 1.19×   |
| 1000   | 345 k | 396 k | 1.15×   |

Dense throughput essentially unchanged (the fast-paths short-circuit
work that wasn't expensive on dense workloads in the first place).

cProfile of sparse-time (50 runs of 100 events at period=1000): wall
time **129 ms → 101 ms (1.28×)**, function calls 412 k → 311 k.
``destroy_active_entity`` and ``handle_external_input_event`` left the
top-15 entirely.

### Hot-path micro-tightening — ✅ Landed

After the HLA port, profiling showed three cheap wins still on the
table:

1. **`SystemObject.__init__` no longer calls `datetime.now()`.** The
   `__created_time` field was only ever read by `__str__` and never
   used elsewhere in pyjevsim. Removing it saves a `datetime.now()`
   per object allocation — meaningful because every `SysMessage`,
   `BehaviorModel`, and executor pays for it.
2. **`ScheduleQueue.push` reads `executor._obj_id` directly** instead
   of through `get_obj_id()`. The id is stable for the executor's
   lifetime; the method dispatch was running 6 000 times per HI 8×8
   run. (`get_req_time()` is *still* a method call because it has
   side effects on the cancel-reschedule flag.)
3. **`schedule()`'s Phase B uses `dst_exec._obj_id`** for the
   active-map check instead of `dst_exec.get_obj_id()`, avoiding
   the same dispatch on every routed output.
4. **`time.perf_counter()` only fires in R_TIME**; the V_TIME and
   HLA paths skip the syscall.
5. **The `condition` lock around `output_event_queue.append` is
   skipped when no output-event callback is registered** (the
   common single-threaded V_TIME setup).

**Realised impact** (cumulative on top of all previous landed work):

| benchmark | before this round | after | speedup |
|-----------|------------------:|------:|--------:|
| LI 4×4    |  272 k            | 344 k | 1.27×   |
| LI 6×6    |  462 k            | 500 k | 1.08×   |
| HI 4×4    |  335 k            | 410 k | 1.22×   |
| HI 6×6    |  542 k            | 616 k | 1.14×   |
| HI 8×8    |  ~626 k           | 715 k | 1.14×   |
| **HI 10×10** | ~708 k         | **844 k** | **1.19×** |
| HO 6×6    |  527 k            | 623 k | 1.18×   |
| Sparse, p=1000 | ~300 k       | 345 k | 1.15×   |

At HI 10×10 pyjevsim now overtakes xdevs (844 k vs 771 k tr/s) — the
heapset scales better than xdevs's per-tick `min(...)` linear scan.

cProfile of HI 8×8 (20 runs): wall time **66 ms → 59 ms (1.12×)**,
function calls 236 k → 216 k.

### HLA `step()` ported to cascade tick — ✅ Landed

The HLA path was previously stuck on the legacy sequential schedule
loop with eager `ext_trans` in `single_output_handling`, which meant
HLA federates inherited the same confluent-transition undercounting
that V_TIME had before the cascade-tick fix. `step(granted_time)` now
uses the same four-phase tick as `schedule()`:

- Phase A pops every imminent at the actual event time (advancing
  `global_time` to it inside the grant window).
- Phase B routes outputs through the coupling map; root-level emits
  hit the `output_event_queue` for the RTI to republish.
- Phase C dispatches `con_trans` / `int_trans` / `ext_trans` correctly,
  matching standard DEVS semantics.
- Phase D bulk-reschedules via `ScheduleQueue`.
- After the loop, `global_time` is set to `granted_time` per
  IEEE 1516-2010 timeAdvanceGrant convention.

Tests in `tests/test_hla_step.py` (4) pin: confluent fires correctly,
intra-grant time advancement, multi-round cascades drain in one
`step()`, and outputs are returned for republishing. Full suite now
40/40 passing.

### dmc routing now opt-in — ✅ Landed (LI-specific win + debug preserved)

The flat DEVStone topology has every LI atomic emitting to a port with
no real downstream coupling, so each emit was being routed to the
`DefaultMessageCatcher`. That catcher's `ext_trans` is a no-op
(`data = msg.retrieve()` then discard) but the routing itself was
expensive: 26 messages per round × `set_req_time` + `ScheduleQueue.push`
on the catcher. For LI 6×6 this dominated per-tick wall time
(450 µs/tick before bypass, 240 µs/tick after).

**Change.** `SysExecutor` accepts a new constructor keyword
``track_uncaught=False`` (default off — the fast path). When set to
``True`` `_destinations_for` and `single_output_handling` install the
old dmc fallback so users can observe uncoupled emits via ``se.dmc``
(the same `DefaultMessageCatcher` that already existed). With the
default, uncoupled emits are genuine no-ops. The dmc model stays
registered either way — only the routing changes.

Two tests pin the contract: `tests/test_track_uncaught.py` confirms
the default drops uncoupled emits and the opt-in routes them.

Measured cost of the debug option (LI 6×6): ~14% throughput drop vs the
default, which is exactly the overhead of running the catcher's
no-op transition through the simulator per uncoupled emit.

**Realised impact:**

| benchmark | small refactors only | + dmc bypass | speedup |
|-----------|---------------------:|-------------:|--------:|
| LI 4×4    |              272 k   |       312 k  |  1.15×  |
| **LI 6×6** |             353 k   |       462 k  |  **1.31×** |
| HI 4×4    |              335 k   |       369 k  |  1.10×  |
| HI 6×6    |              512 k   |       542 k  |  1.06×  |
| HO 4×4    |              345 k   |       361 k  |  1.05×  |
| HO 6×6    |              527 k   |       552 k  |  1.05×  |
| Sparse, p=1000 |          297 k  |       316 k  |  1.06×  |

LI shows the biggest jump because most LI emits had no real receiver.
HI/HO improve less because their chain couplings already absorb most
emits — only the chain-tail and innermost atomics had been routing to
dmc.

### Small-refactor wave — ✅ Landed (post-T1.2 cleanup)

After the heapset landed, profiling pinned the remaining hot spots on
per-transition method dispatch and lock contention rather than data
structure work. Three targeted refactors:

1. **Cache `obj_id`.** `BehaviorExecutor.__init__` snapshots
   `behavior_model.get_obj_id()` into `self._obj_id`. `get_obj_id()`
   returns the cached value. Removes the `BehaviorExecutor` ->
   `BehaviorModel` -> `SystemObject` dispatch chain from every
   `ScheduleQueue.push`. Same change on `StructuralExecutor`.

2. **Inline `set_req_time`.** Folded `set_global_time` + `time_advance`
   + the `_cancel_reschedule_f` arithmetic into one method body in
   `behavior_executor.py`. Eliminates 3-4 method calls per affected
   model per tick.

3. **Drop the V_TIME condition lock from the hot path.** Removed
   `with self.condition:` from `simulate()`'s pause-check (now a
   read-only check that only locks when actually paused) and from
   `schedule()` Phase E's `global_time` write. Pause/resume,
   `insert_external_event`, and `set_output_event_callback` still take
   the lock themselves where it matters; CPython attribute writes are
   atomic at the bytecode level so the simulator's own time advance is
   safe without it.

**Realised impact** (all 34 tests still pass):

| benchmark | heapset only | + small refactors | speedup |
|-----------|-------------:|------------------:|--------:|
| HI 4×4    |      301 k   |          335 k    |  1.11×  |
| HI 6×6    |      462 k   |          512 k    |  1.11×  |
| HO 4×4    |      311 k   |          345 k    |  1.11×  |
| HO 6×6    |      481 k   |          527 k    |  1.10×  |
| LI 6×6    |      327 k   |          353 k    |  1.08×  |
| Sparse, p=100 | 260 k    |          304 k    |  1.17×  |

cProfile of HI 8×8 (20 runs): wall time **73 ms → 66 ms (1.10×)**,
function calls 268 k → 236 k. `set_req_time` per-call cost dropped
from 488 ns to 326 ns. `get_obj_id` left the top-15 entirely.

### T1.2  Heapset priority queue — ✅ Landed

**Status.** `pyjevsim/schedule_queue.py` is now a heapset — heap of
*unique timestamps* + `dict[time → set(executor)]`, the same structure
PythonPDEVS uses in `SchedulerHS`. Same public API
(`push / pop / peek_time / remove`) plus a new `pop_all_at(time)` that
drains a whole bucket in one dict lookup. `SysExecutor.schedule()`'s
Phase A uses `pop_all_at` so dense same-time cascades pay O(1) instead
of O(K log U). `StructuralExecutor` uses the same class. Counterpart
changes: `Executor.__lt__` deleted, `_in_heap` set and `_schedule_dirty`
flag removed; no `heapify` calls remain.

The migration was staged: an intermediate lazy-deletion heap landed
first (sparse-time-friendly, simpler), then was rewritten as the
heapset for the dense-DEVStone win.

**Realised impact** (vs pre-T1.2 cascade-tick baseline):

| benchmark              | before | lazy heap | heapset | total |
|------------------------|-------:|----------:|--------:|------:|
| LI 6×6                 | 290 k  |   304 k   |  327 k  | 1.13× |
| HI 4×4                 | 258 k  |   287 k   |  301 k  | 1.17× |
| HI 6×6                 | 349 k  |   432 k   |  462 k  | 1.32× |
| HO 4×4                 | 251 k  |   300 k   |  311 k  | 1.24× |
| HO 6×6                 | 351 k  |   436 k   |  481 k  | 1.37× |
| Sparse, all periods    | ~265 k |  ~265 k   | ~265 k  | flat  |

cProfile on HI 8×8 (20 runs): wall time **110 ms → 73 ms (1.51×)**,
function calls 493 k → 268 k. Heap bookkeeping cost collapsed from
~42 % of runtime to under 10 %.

> Cross-engine design analysis lives in
> [`t1_2_scheduler_analysis.md`](t1_2_scheduler_analysis.md). The cascade
> proposal in [`cascade_scheduling_proposal.md`](cascade_scheduling_proposal.md)
> landed before T1.2 (as the confluent-bug fix); both stack cleanly.


`pyjevsim/schedule_queue.py` already implements a lazy-deletion priority queue,
but `SysExecutor` still uses a raw `min_schedule_item` list with manual
`heapq.heapify(...)` calls every time `_schedule_dirty` is set
(`system_executor.py:382-384`, `:216-218`, `:599-601`) and `StructuralExecutor`
does the same (`pyjevsim/structural_executor.py:78-84`, `:114-115`).
`heapify` is O(N); doing it inside the inner schedule loop turns a
log-N operation into a linear one and dominates the HI/HO benchmarks.

**Change.** Replace the bare lists with `ScheduleQueue.push/pop/remove`.
`set_req_time` becomes a re-push (lazy invalidation), so nothing in the inner
loop needs to heapify. Mirror the change in `StructuralExecutor`.

**Expected impact.** Big on HI/HO and any graph with high fan-out
(N proportional to width × depth). Benchmarks suggest 1.5x–3x.
**Risk.** Low — `ScheduleQueue` is already in-tree and mirrors the semantics.
**Complexity.** Medium; touches two executors and `destory_entity`.

### T1.3  Remove the dead `copy.deepcopy` branch in output handling

`output_handling` calls `copy.deepcopy(pair)` for every message in a
list-typed contents entry (`system_executor.py:341`). The branch is
**dead code that crashes when exercised** — `pair = (model, msg)` includes
the source model whose ancestor (`SysExecutor`) holds a
`threading.Condition`, so `copy.deepcopy` raises
`TypeError: cannot pickle '_thread.RLock' object`. Even if the deepcopy
succeeded, the result is a tuple but the callee
(`single_output_handling`) treats it as a `SysMessage` (`msg.get_dst()`).
Empirically verified — see `benchmark/aliasing_test.py`.

The aliasing hazard the deepcopy was nominally guarding against also does
not exist in any engine in the comparison set: xdevs, pypdevs, and the
reference engine all share value references across multi-subscribers (see
`benchmark/results/ALIASING.md`). The Python-DEVS convention is "outputs
are conceptually immutable; copy on the receiver side if you need to
mutate."

**Change.** Drop the `isinstance(msg, list)` branch entirely. Document the
shared-reference convention in the `BehaviorModel` / `SysMessage` docstring
and the README.

**Expected impact.** Removes one Python-level branch from the inner loop,
plus the latent bug. **Risk.** Low — the branch cannot be running today.
**Complexity.** Trivial.

### T1.4  Avoid lock acquisition per output event in V_TIME

`single_output_handling` enters `with self.condition:` for every external
output event (`system_executor.py:318-319`) and `handle_external_input_event`
acquires the same lock once per tick. In V_TIME single-threaded mode the lock
is pure overhead (CPython acquires/releases a `threading.RLock` on every call).

**Change.** Either skip the lock when no external producer is registered
(`_output_event_callback is None and not multithreaded`), or batch the
appends and acquire the lock once per `schedule()` call.

**Expected impact.** 5–15% on output-heavy workloads (HO variant in the
benchmark). **Risk.** Low; gate the fast path on a flag set when external
threads are connected. **Complexity.** Small.

---

## Tier 2 — moderate impact, moderate effort

### T2.1  Replace O(N²) `destory_entity`

`destory_entity` (`system_executor.py:189-218`) iterates `self.port_map.items()`
once per agent, then does `agent in self.min_schedule_item` (linear) and a
final `heapq.heapify`. Removing K agents from a graph of N ports is
O(K · (N + N) + K · N) — quadratic when teardowns are batched.

**Change.** Maintain reverse indexes: `agent -> set(out_keys)` and
`agent -> set(in_couplings)` rebuilt incrementally inside `coupling_relation`.
Removal becomes O(degree). Combine with T1.2 to drop the heapify.

**Expected impact.** Only matters for simulations with large entity churn
(spawning/destroying many models). **Risk.** Low. **Complexity.** Medium.

### T2.2  Cache `time_advance` lookups

`BehaviorExecutor.time_advance()` (`pyjevsim/behavior_executor.py:103-108`)
does a dict lookup into `behavior_model._states` on every call. The state
typically changes only on transitions; the deadline is constant within a
state.

**Change.** Recompute `_cached_time_advance` in `init_state`/`_cur_state`
setters and have `time_advance()` return the cached value. `set_req_time`
becomes a single addition.

**Expected impact.** 5–10% on transition-heavy workloads. **Risk.** Low —
states are immutable post-construction in current models. **Complexity.**
Small but requires a setter discipline.

### T2.3  Eliminate `isinstance(msg, list)` branch in output handling

`output_handling` (`system_executor.py:336-343`) accepts both bare messages
and lists of messages, requires the deepcopy noted in T1.3, and forces an
isinstance check per message. The two-shape contract makes the hot path
branchy.

**Change.** Tighten `MessageDeliverer.insert_message` to flatten lists at
insertion time so `output_handling` can iterate a single uniform sequence.
Update any caller that relies on the list shape (none in core, audit
examples).

**Expected impact.** ~3–5% plus removes the deepcopy. **Risk.** Low/medium.
**Complexity.** Small.

### T2.4  Fast-path `single_output_handling` cache

For every output, the function does `pair = (obj, msg.get_dst())` and a
dictionary lookup, falling back to a default-message-catcher binding
(`system_executor.py:305-309`). The fallback creates a new tuple every miss.

**Change.** Pre-bind `(obj, port) -> destinations` at coupling time, including
a default `[(dmc_executor, "uncaught")]` for ports the model declares but
nobody listens on. `single_output_handling` becomes a single dict lookup +
loop.

**Expected impact.** Minor (~3%) but compounds with T1.2.
**Risk.** Low. **Complexity.** Small.

### T2.5  Faster `Executor.__lt__`

`Executor.__lt__` (`pyjevsim/executor.py:26-27`) recomputes a 2-tuple per
comparison. Each `heappush`/`heappop` calls it O(log N) times.

**Change.** Either keep the comparison key as a precomputed
`(request_time, obj_id)` attribute, or rely on the entry tuple already used
by `ScheduleQueue` (`(req_time, obj_id, entry_id, executor)`) so the executor
is never compared directly.

**Expected impact.** Small on its own; folds into T1.2 essentially for free.
**Risk.** Low. **Complexity.** Trivial when combined.

---

## Tier 3 — strategic / exploratory

### T3.1  Optional Cython / mypyc compilation of the inner loop

`SysExecutor.schedule`, `BehaviorExecutor.set_req_time`, and `ScheduleQueue`
operations dominate profiling output. They are pure-Python, statically typed
in spirit, and good targets for `mypyc` or a thin Cython layer.

**Expected impact.** 1.5x–3x on CPython, possibly more. **Risk.** Adds a
build step; needs a fallback for users who only `pip install`. **Complexity.**
Medium-large; treat as a post-Tier-1 effort.

### T3.2  PyPy compatibility pass

Run the test suite and benchmark under PyPy. The simulator is a textbook
PyPy-friendly workload (lots of small Python objects, hot loops). If nothing
breaks, document the speedup and recommend PyPy for batch runs.

**Expected impact.** 3x–10x with no code changes if it works. **Risk.**
`dill` and snapshot serialisation may need tweaks. **Complexity.** Mostly a
testing exercise.

### T3.3  Batched external-event drain

`handle_external_input_event` (`system_executor.py:586-601`) pops events one
at a time under the lock and calls `output_handling` in a loop. For bursty
producers, drain the entire queue in one critical section, then dispatch
without holding the lock.

**Expected impact.** Helps multithreaded HLA / R_TIME workloads. Negligible
in V_TIME single-thread benchmarks. **Risk.** Low. **Complexity.** Small.

### T3.4  Optional `SysMessage` pooling

Each scheduled event allocates one `SysMessage` and one `MessageDeliverer`.
A reusable pool keyed by source model would avoid GC pressure in
allocation-heavy runs.

**Expected impact.** Modest (5–10%) on CPython, less under PyPy. **Risk.**
Pool reuse interacts with snapshotting — must reset state on release.
**Complexity.** Medium.

### T3.5  Snapshot/restore overhead audit

When `snapshot_manager` is set, every executor is wrapped by a
`SnapshotExecutor` (`pyjevsim/snapshot_factory.py`). Confirm the wrapper has
no overhead when no snapshot is requested for a given tick — one extra method
call per transition is enough to register on benchmarks.

**Expected impact.** Only relevant when snapshot_manager is configured.
**Risk.** Low. **Complexity.** Small.

### T3.6  Numerical time as integers in V_TIME

Floating-point `global_time` introduces drift and (minor) FP comparison cost
in the hot loop. For pure V_TIME runs, an integer tick counter scaled by
`time_resolution` would be faster and less surprising.

**Expected impact.** Marginal performance, larger correctness benefit.
**Risk.** API surface change — gate behind a constructor flag.
**Complexity.** Medium.

---

## Measurement methodology

Use `benchmark/run_devstone.py --sweep` as the regression gate:

1. Capture baseline numbers on `main` before any change.
2. For each tier-1 item, regenerate the sweep and diff CSV columns
   `transitions`, `events_per_s`, `sim_time_s`.
3. Profile with `python -m cProfile -o devstone.prof -m benchmark.run_devstone
   --variant hi --depth 5 --width 4 --events 200` and compare the top callers.
4. Track results in `benchmark/results/` so improvements are reproducible.

Suggested ordering: T1.1 → T1.2 → T1.3 → T1.4 → T2.x cluster → T3.x as
follow-on. T1.1 and T1.2 are independent and can be parallelised; T1.3 and
T2.3 should land together to avoid two passes over `output_handling`.
