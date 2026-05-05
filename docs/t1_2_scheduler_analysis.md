# T1.2 — Scheduler Design Gap Across Python DEVS Engines

## Why this analysis

T1.1 (V_TIME jump-to-next-event) closed the sparse-time gap. The dense-DEVStone gap remains: pyjevsim is 3.7× slower than xdevs and 5× slower than PythonPDEVS on workloads where every event lives at the same simulated time. The cProfile data points squarely at the priority-queue: `Executor.__lt__` and `heapq.heapify` together account for ~63 % of pyjevsim's simulation time on HI 8×8.

Before swapping data structures, it pays to understand what every engine in the comparison set actually does — these are the four mature designs in the Python-DEVS ecosystem and their tradeoffs are well-documented in the PyPDEVS scheduler family.

## The four designs side by side

| engine            | structure                                              | key  | reschedule cost          | min-lookup cost          |
|-------------------|--------------------------------------------------------|------|--------------------------|--------------------------|
| pyjevsim (today)  | raw `heapq` + `heapify` on dirty                       | model | O(N) per dirty event    | O(1) (`heap[0]`)         |
| xdevs.py          | linear scan over processors                            | model | O(1) attribute write    | O(N) per tick (`min()`)  |
| pypdevs `SchedulerHS` (default) | heap of **unique timestamps** + dict[t→set(models)]    | time  | O(log U) when t is new, O(1) when t already in heap | O(1) |
| reference engine  | flat heap of `(time, counter, atomic)` tuples + lazy invalidation | time | O(log N)            | O(1) (`heap[0]`)         |

`N` = number of models in the FEL. `U` = number of *unique* timestamps in the FEL — typically << N when many events fire at the same simulated time (the DEVStone case) or activate in bursts.

## How each design behaves under the DEVStone workload

DEVStone HI 8×8: ~50 atomics, every transition lives at the same simulated instant (t=0). Single seed event triggers a cascade.

### pyjevsim (heapq + heapify-on-dirty)

`SysExecutor.schedule()` (`pyjevsim/system_executor.py:362-432`) pops one item, fires it, sets `_schedule_dirty = True` whenever an output triggers an `ext_trans` on a receiver, then `heapq.heapify(self.min_schedule_item)` repairs the heap. For HI 8×8 that means 52 calls to `heapify` per simulation, each O(N=51).

Comparison cost compounds the issue: `Executor.__lt__` (`pyjevsim/executor.py:26-27`) recomputes `(self.request_time, self.get_obj_id())` on each side, and `get_obj_id` dispatches across two layers (`BehaviorExecutor` → `SystemObject`). 103 360 comparisons across 20 runs → ~410 k method calls just to fetch IDs.

Profile: ~63 % of total simulation time on HI 8×8.

### xdevs.py (linear scan)

`Coordinator.ta()` (`xdevs/sim.py:248-249`):

```python
def ta(self):
    return min((proc.time_next for proc in self.processors), default=INFINITY) - self.clock.time
```

Each tick walks every child processor to compute the time advance and again to find imminent processors (`imminent_processors`, line 186-187). No heap. Reschedule is just `proc.time_next = ...` — a pure attribute write, O(1).

For DEVStone, where the cascade collapses to ~1 tick of simulated time, this means ~50 attribute reads. Far cheaper than pyjevsim's heap maintenance, even though asymptotically it's worse: O(N) per tick is fine when there are few ticks.

The architecture is **hierarchical**: each Coupled has its own Coordinator that delegates to children. ta() and lambdaf() recursively descend, so an N-component graph still does O(N) work but spread across hierarchy levels. xdevs supports `flatten=True` to collapse the hierarchy when it hurts.

### pypdevs `SchedulerHS` (heapset)

The data structure is the inverse of pyjevsim's:

- The heap stores **unique timestamps** only.
- A `dict[time → set(models)]` holds the models scheduled at each time.
- A `reverse: list[model_id → previous_time]` lets reschedule update the right bucket.

Reschedule (`pypdevs/schedulers/schedulerHS.py:84-108`):

```python
for model in reschedule_set:
    self.mapped[self.reverse[model.model_id]].remove(model)
    self.reverse[model.model_id] = tn = model.time_next
    try:
        self.mapped[tn].add(model)
    except KeyError:
        self.mapped[tn] = {model}
        heappush(self.heap, tn)            # only when this timestamp is brand new
```

For DEVStone the entire cascade lives at t=0. The heap has **one** entry: `(0,)`. Reschedule is just dict ops. No `heapify` ever runs. This is why pypdevs is 5× faster than pyjevsim on HI 6×6: same Python overhead per atomic, but the priority-queue overhead is essentially zero.

`readFirst()` skips empty buckets:

```python
first = self.heap[0]
while len(self.mapped[first]) == 0:
    del self.mapped[first]
    heappop(self.heap)
    first = self.heap[0]
```

So time progression amortises at O(log U) where U is the count of distinct timestamps actually used.

### Reference engine (flat lazy heap)

`benchmark/engines/reference/engine.py` keeps a single `(time, counter, atomic)` heap. The counter breaks ties without invoking `__lt__` on the atomic. There's no in-place reschedule — instead, push a fresh entry and ignore stale ones on pop. With 50 atomics in a single-tick cascade, this is ~50 pushes + 50 pops, O(log N) each.

This is essentially the same data structure pyjevsim already has in `pyjevsim/schedule_queue.py:8-54` — but pyjevsim does not use it.

## What pyjevsim has but doesn't use

```python
class ScheduleQueue:
    def push(self, executor):
        req_time = executor.get_req_time()
        entry_id = next(self._counter)
        entry = (req_time, executor.get_obj_id(), entry_id, executor)
        self._entries[executor.get_obj_id()] = (req_time, entry_id)
        heapq.heappush(self._heap, entry)

    def pop(self):
        while self._heap:
            req_time, obj_id, entry_id, executor = heapq.heappop(self._heap)
            current = self._entries.get(obj_id)
            if current and current == (req_time, entry_id):
                del self._entries[obj_id]
                return executor
        raise IndexError("pop from empty ScheduleQueue")
```

This is a textbook **lazy-deletion heap**. Push is O(log N). Pop discards stale entries cheaply (the inner loop is amortised O(log N)). No `heapify` ever runs because reschedule is just "push a new entry; ignore the old one when it surfaces". And the heap key is a flat tuple — no `Executor.__lt__` call.

`Executor.__lt__` becomes irrelevant once you store tuples on the heap; the `(req_time, obj_id, entry_id, executor)` ordering is settled by the first three (immutable) fields. That folds T2.5 in for free.

## The design choice for T1.2

Three viable paths:

### Option A — Adopt the existing `ScheduleQueue` as-is

**Pros.**
- Already in the repo. Tested in spirit (matches the AH pattern from pypdevs, ADEVS, VLE).
- One PR: replace `min_schedule_item` reads/writes with `ScheduleQueue` calls in `system_executor.py` and `structural_executor.py`.
- `Executor.__lt__` becomes dead code — T2.5 free.

**Cons.**
- Still O(N log N) on cascades because each model gets its own heap entry. xdevs (linear scan) and pypdevs (heapset) are both faster on dense workloads where many models fire at the same time.

**Expected impact.** Should close most of the gap to xdevs (3.7× → ~1.5–2×). The 60% of time currently spent in `heapify` + `__lt__` evaporates; the residual is per-transition Python overhead.

### Option B — Build a heapset (SchedulerHS-style) in pyjevsim

**Pros.**
- Asymptotically the right thing for DEVStone-shape workloads. Closes the gap to pypdevs (5× → ~1.5×).

**Cons.**
- New code, not a port of an existing class. Needs careful handling of the "previous time" reverse map, the empty-bucket skip in `readFirst`, and the infinity sentinel that pypdevs got wrong on the empty-heap case (we already had to patch that).
- Most pyjevsim simulations are not dense-cascade-shaped — for normal application workloads, lazy-deletion heap is more than enough.

**Expected impact.** Bigger win than Option A but with materially more risk and more code to maintain.

### Option C — Hybrid like `SchedulerAuto`

Pypdevs's `SchedulerAuto` switches between SchedulerML (linear list) and SchedulerHS based on access patterns. Almost certainly overkill for pyjevsim's stage of maturity — adds two implementations plus a switching policy.

## Recommendation

**Land Option A first.** Five reasons:

1. The class `pyjevsim/schedule_queue.py` already exists and was clearly intended for this purpose.
2. The diff is small and the test surface is the existing test suite plus the benchmark sweeps.
3. T2.5 (faster `Executor.__lt__`) folds in for free.
4. Realistically closes most of the gap to xdevs. The remaining gap to pypdevs is workload-shape-specific (DEVStone-like cascades).
5. After A lands, profile again. If the residual time is still dominated by per-model rescheduling on dense workloads, *then* consider the heapset upgrade with concrete numbers showing it's worth the code.

## Implementation sketch for Option A

Rough scope, ~50 LOC of changes plus deletions.

1. Replace `self.min_schedule_item: list` with `self.fel: ScheduleQueue` in `SysExecutor.__init__`.
2. Replace `heapq.heappush(self.min_schedule_item, obj)` with `self.fel.push(obj)`.
3. Replace `heapq.heappop(self.min_schedule_item)` with `self.fel.pop()`.
4. Replace `heapq.heapify(self.min_schedule_item) ; self._schedule_dirty = False` blocks with **nothing** — lazy deletion makes them obsolete. Delete `_schedule_dirty` entirely.
5. Replace `self.min_schedule_item[0].get_req_time()` (peek) with `self.fel.peek_time(default=Infinite)`.
6. In `output_handling.single_output_handling` (`system_executor.py:296-326`), replace `destination[0].set_req_time(self.global_time); self._schedule_dirty = True` with `destination[0].set_req_time(self.global_time); self.fel.push(destination[0])` — the old entry remains in the heap but is now stale and gets skipped on the next pop.
7. Mirror the change in `StructuralExecutor` (`pyjevsim/structural_executor.py`).
8. After verifying nothing breaks, delete `Executor.__lt__` (it's no longer called) and the unused tuple comparison in `executor.py:26-27`.

`ScheduleQueue` may need two minor additions:
- `__init__` should accept an iterable of pre-existing executors (init_sim use).
- A `discard(obj_id)` for `destory_entity` cleanup so we don't leak entries when models are removed.

## Validation plan

1. `pytest tests/` — all 30 must still pass.
2. `python -m benchmark.run_compare` — capture the new dense-DEVStone tr/s numbers; gap to xdevs should drop substantially.
3. `python -m benchmark.run_sparse` — should stay flat (T1.1 untouched).
4. Re-profile with cProfile on HI 8×8 — the `__lt__` and `heapify` lines should disappear from the top-20.
5. `examples/banksim/banksim.py` and `examples/atsim/simulator.py` — smoke-test that nothing user-visible regressed.

## Forward-looking notes

- The lazy heap pattern is commonly attributed to *Brown, "Calendar Queues" (1988)* in the broader DES literature; it's standard in ADEVS, VLE, and OMNeT++. PyPDEVS's `SchedulerAH` is the same pattern; `SchedulerHS` is the timestamp-indexed extension that wins when many models fire simultaneously.
- The gap between Option A and Option B is essentially the ratio (number of models scheduled per tick) / (number of unique timestamps). DEVStone collapses everything to t=0 so the ratio is high — that's why pypdevs has its biggest lead there. Real applications with stochastic or evenly-spread event times see a much smaller gap, which is another reason A is enough for now.
- After A lands, the cleanest follow-on win is **T1.4 (skip the lock in V_TIME single-threaded mode)** rather than chasing the heapset. The heapset only matters under DEVStone-like workloads; the lock matters on every single output.
