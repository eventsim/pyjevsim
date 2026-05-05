# Cascade-Aware Two-Phase Scheduling for pyjevsim

## The starting observation

Rescheduling in DEVS is triggered by exactly two kinds of event:

1. **Deadline reached.** A model `X` whose `req_time` matches the current
   simulated time pops off the priority queue, fires `λ` (output), then
   does its internal transition. Both steps change `X`'s next deadline.

2. **External event delivered.** A model `Y` whose input port receives a
   message executes `δ_ext`. That changes `Y`'s phase, and therefore its
   `time_advance()`, and therefore its next deadline.

These two triggers are not independent. Trigger (1) **causes** a wave of
trigger (2)s in the same simulated instant: when `X.λ` produces messages,
every model coupled to `X`'s output port receives an external event at
that instant. So at any tick `T`, the set of models whose deadline must
be recomputed is

    affected(T) = imminent(T) ∪ ⋃ subscribers(X)  for X in imminent(T)

Today's pyjevsim ignores this structure. It pops one model, immediately
calls `ext_trans` on each subscriber inside `output_handling`, marks
`_schedule_dirty = True`, and forces a full `heapq.heapify` on the next
iteration of the inner loop (`pyjevsim/system_executor.py:362-432`). Each
subscriber's deadline change triggers a separate O(N) heap repair, even
though we already know — from the coupling map — exactly which models
are affected before we start.

## The proposal

A **two-phase tick** that uses the coupling map to plan all reschedules
for the current instant up front, then commits them in a single batched
operation.

```
Phase A — collect outputs
  imminent  = pop_all_at(T)         # models whose req_time == T
  outputs   = {}                     # X → list of (out_port, value)
  for X in imminent:
      outputs[X] = X.λ()

Phase B — route + classify
  influenced_inputs = {}             # Y → [(in_port, value)]
  for X, out_list in outputs.items():
      for (out_port, value) in out_list:
          for (Y, in_port) in coupling[(X, out_port)]:
              influenced_inputs.setdefault(Y, []).append((in_port, value))

  influenced = set(influenced_inputs)
  affected   = imminent | influenced

Phase C — apply transitions in one pass
  for M in affected:
      bag = influenced_inputs.get(M, [])
      if M in imminent and bag:        # confluent
          M.con_trans(bag)
      elif M in imminent:
          M.int_trans()
      else:
          M.ext_trans(bag)             # bag, not single message — Parallel DEVS

Phase D — bulk reschedule
  for M in affected:
      fel.push(M, T + M.time_advance())   # lazy: stale entry filters on pop
```

The four phases run **once per simulated instant**. Inside each, every
model touches the schedule queue at most once. The heap is never
re-heapified — phase D uses `ScheduleQueue.push` (lazy invalidation, see
`pyjevsim/schedule_queue.py:8-54`), so old entries simply get skipped on
the next pop.

## Why this is structurally faster than what pyjevsim does today

Comparing the per-tick work for a tick where `K` models in the imminent
set fire and they collectively wake `M` subscribers (so `affected = K + M`
unique models, FEL of size `N`):

| operation | today | proposal |
|-----------|-------|----------|
| heap pops | `K` (one per imminent) interleaved with phase-A/B/C | `K` (batched) |
| `ext_trans` invocations | `M` (one per delivery) | one per receiver, with the full bag |
| heap-repair cost | up to `K` × `heapify(N)` = `O(K · N)` | 0 (lazy `push` only) |
| `__lt__` calls | `K · O(log N)` per heapify, dominated by heapify cost | `(K + M) · O(log N)` for the pushes |
| `heapq.heapify` calls | `K` (one per dirty event) | 0 |
| confluent firings | not handled distinctly (see semantics section) | exactly `K ∩ M` |

For the dense DEVStone case (HI 8×8: K ≈ 1, M ≈ 50, N ≈ 51), today's
algorithm pays roughly 50 × 51 ≈ 2 500 comparisons per cascade for heapify
work alone. The proposal pays `(1 + 50) × log(51) ≈ 290` comparisons.
Order-of-magnitude reduction in the bottleneck the cProfile traced.

## What changes about correctness

This is the part worth being explicit about — it is not purely an
optimisation. Today's loop has a subtle ordering quirk and a missing
case.

### Ordering quirk in the current code

`output_handling` calls `destination[0].ext_trans(...)` for every
subscriber **before** `tuple_obj.int_trans()` runs on the firer
(`system_executor.py:322-326` then `:377`). So at simulated time `T`:

1. `X.λ` produces output.
2. `Y.ext_trans` runs (Y now in some new phase).
3. `X.int_trans` runs (X transitions afterwards).

Most DEVS abstract simulators place all `λ` calls before any transition,
not interleaved with them. The proposal moves `X.int_trans` into Phase C
alongside everyone else, restoring the standard Parallel DEVS schedule.

### The missing confluent case

Classic DEVS uses three transition functions: `δ_int`, `δ_ext`, `δ_con`.
`δ_con` runs when a model is *both* imminent and receiving external
events at the same simulated instant. xdevs and pypdevs both implement
this (default: `δ_con = δ_int; δ_ext`). pyjevsim's `BehaviorModel` has
only `int_trans` and `ext_trans`.

This is visible in the cross-engine baseline:

| variant | pyjevsim transitions | xdevs / pypdevs / reference transitions |
|---------|----------------------|------------------------------------------|
| HI 4×4  | 26                   | 38                                       |
| HI 6×6  | 72                   | 152                                      |

The gap is exactly the confluent firings that pyjevsim drops because
`output_handling` invokes `ext_trans` only and `int_trans` runs on a
different "tick" (see ordering quirk above).

The proposal introduces:

```python
class BehaviorModel:
    def con_trans(self, port_msgs):
        """Confluent transition. Default: int then ext (matches xdevs)."""
        self.int_trans()
        for port, msg in port_msgs:
            self.ext_trans(port, msg)
```

Existing models keep working — they inherit the default. Models that
care can override.

### `ext_trans` becomes bag-based

Today's pyjevsim calls `ext_trans(port, msg)` once per delivered message
(`single_output_handling`, `system_executor.py:296-326`). If two
producers fire into the same input port at the same instant, the
receiver's `ext_trans` runs twice in sequence with potentially
inconsistent intermediate state.

Parallel DEVS hands `ext_trans` the *bag* of all messages that arrived
in this instant. The proposal does the same. Backwards-compatibility
shim:

```python
class BehaviorModel:
    def ext_trans_bag(self, port_msgs):
        """Override for true bag semantics. Default: replay one-at-a-time."""
        for port, msg in port_msgs:
            self.ext_trans(port, msg)
```

Old models work; new models can opt into bag semantics by overriding the
bag method.

## Where the savings come from, concretely

The proposal exploits four facts that today's algorithm ignores:

1. **The coupling map is known statically.** Given `X` and the port it
   fires on, we can list every receiver in O(degree). We don't need to
   discover them by routing messages through the heap.
2. **At any one instant, most models don't change.** With `affected`
   computed up front, models *not* in `affected` are guaranteed not to
   need reschedule. Today's `_schedule_dirty` flag forces a global
   `heapify` that touches all `N` entries even when only `M+K` changed.
3. **Lazy invalidation handles in-place reschedule for free.**
   `ScheduleQueue.push` adds a new entry; the old one is filtered on
   pop. No `heapify` at all is needed when models are only ever moved
   *forward* in time — which is the only reschedule direction in DEVS.
4. **The simulated-instant boundary is a natural batching unit.** All
   transitions and reschedules at instant `T` can be deferred until
   we've collected the full `affected` set, then committed as a batch.
   Today's algorithm interleaves discovery and commit, which is what
   forces the dirty-flag dance.

## Algorithm in full

```python
def step(self, target_time):
    """Run one simulated-instant tick. Advances global_time afterwards."""
    # Drain external producer events that should fire by now.
    self._handle_external_input_event()

    # Phase A — collect outputs from every imminent model.
    now = self.global_time
    imminent = self.fel.pop_all_at(now)         # may be empty
    if not imminent:
        # Nothing fires; advance time per T1.1 (jump-to-next-event)
        next_t = self._peek_next_event_time()
        self.global_time = min(next_t, target_time)
        return

    outputs = {}
    for X in imminent:
        bag = MessageDeliverer()
        X.output(bag)
        if bag.has_contents():
            outputs[X] = list(bag.get_contents())

    # Phase B — route outputs, build influenced-input map.
    influenced_inputs = {}                       # Y -> [(in_port, msg)]
    for X, msgs in outputs.items():
        for msg in msgs:
            for (Y, in_port) in self._destinations(X, msg.get_dst()):
                influenced_inputs.setdefault(Y, []).append((in_port, msg))

    affected = set(imminent) | influenced_inputs.keys()

    # Phase C — apply transitions in one classification pass.
    imminent_set = set(imminent)
    for M in affected:
        bag = influenced_inputs.get(M, ())
        if M in imminent_set and bag:
            M.con_trans(bag)
        elif M in imminent_set:
            M.int_trans()
        else:
            M.ext_trans_bag(bag)

    # Phase D — bulk reschedule via lazy push (no heapify).
    for M in affected:
        ta = M.time_advance()
        if ta < float("inf"):
            M.set_req_time(now)                  # set model's view of now
            self.fel.push(M)                     # push (now+ta, ...) — old entry stale

    # Phase E — clean up destroyed entities + advance time per T1.1.
    self._destroy_active_entity()
    self.global_time = min(self._peek_next_event_time(), target_time)
```

Helpers needed:

- `ScheduleQueue.pop_all_at(t)` — pop every entry whose `req_time == t`,
  return them as a list, skipping stale entries. ~10 LOC on top of
  `pyjevsim/schedule_queue.py`.
- `SysExecutor._destinations(src, port)` — wraps the existing
  `port_map` lookup with the default-message-catcher fallback. Already
  exists inline in `single_output_handling`.

## Per-instant complexity

| symbol | meaning |
|--------|---------|
| `K`    | imminent models at this instant |
| `M`    | unique receivers reached by their λ outputs |
| `D`    | average coupling fan-out per output port |
| `N`    | size of FEL |

Total work per instant:

- Phase A: `K` λ calls + `K` `pop` ops on the FEL (lazy → O(log N) amortised).
- Phase B: `K · D` lookups in `port_map` + dictionary inserts.
- Phase C: `K + M` transition calls.
- Phase D: `K + M` `push` ops on the FEL (O(log N) each).

Total: **O((K + M) · log N + K · D)**, no heapify.

Today's algorithm: **O(K · N + K · D)** because of the per-event
`heapify`. For DEVStone HI 8×8 with K ≈ 1, M ≈ 50, N ≈ 51, that's
~50× less heap work, plus the elimination of the per-call
`Executor.__lt__` overhead (T2.5 folded in).

## Migration shape

The change is bigger than T1.2 (which was just "swap the data
structure"). It touches semantics, so it deserves its own staging:

1. **T1.2 first** — adopt `ScheduleQueue` *with the current ordering*.
   Smaller diff, no semantic change. Closes the heapify gap to xdevs.
2. **Then this proposal** — repaint `schedule()` as the two-phase tick
   above. The diff is now isolated to one method (`schedule()`) plus
   the new `con_trans` / `ext_trans_bag` defaults on `BehaviorModel`.

Doing them separately lets the cross-engine baseline measure each step
in isolation. The DEVStone HI / HO transition counts should converge to
xdevs/pypdevs values once the two-phase tick lands — that's the
empirical signal that confluent semantics is now correct.

## Validation plan

1. `pytest tests/` — all 30 must pass. Existing models inherit the
   default `con_trans = int_trans + ext_trans` so behaviour is preserved
   for the non-confluent cases the test suite exercises.
2. Add a confluent test: two producers emitting into one receiver at the
   same instant, plus a self-firing model that's both imminent and
   receiving. Assert the receiver's transition is `con_trans`, not two
   separate `ext_trans` followed by an `int_trans` later.
3. Re-run `benchmark.run_compare`. Expectations:
   - LI numbers unchanged (no confluent involved).
   - **HI / HO transition counts converge to xdevs / pypdevs values
     (38 / 152 instead of pyjevsim's current 26 / 72 for d4w4 / d6w6).**
     This is the empirical proof that the confluent fix landed.
   - Wall-clock improvement on top of T1.2 — the heapify removal plus
     the inner-loop tightening should give another 1.5–2× on dense
     workloads.
4. cProfile re-check on HI 8×8. The `__lt__` and `heapify` lines should
   be gone; the new top-line callers should be the transition functions
   themselves (which is what we want — Python overhead in the hot path
   is now spent on user code, not on bookkeeping).

## Risks / things to watch

- **Zero-time loops.** A model with `time_advance() == 0` that keeps
  firing without changing phase will never advance simulated time.
  Today's algorithm hides this because the inner `while` loop processes
  a finite cascade per tick. The two-phase tick has the same property
  *per phase pass*, but the outer loop will still spin. Add a
  per-instant safety counter (e.g. "no model may fire more than `K_max`
  times at the same instant") and raise a clear diagnostic.

- **External-event injection between phases.** Single-threaded V_TIME
  is fine. For external producers (R_TIME / HLA), document that
  injections are visible only at the next phase boundary, never
  mid-phase.

- **Order-sensitive user code.** Some pyjevsim users may have written
  models that assume `ext_trans` is invoked in a specific order across
  receivers (today: insertion order in the inner pop sequence). The
  proposal preserves insertion order within `affected` because dict
  iteration is insertion-ordered in CPython 3.7+, and we add to
  `influenced_inputs` in coupling-map order.

## What we get if we land it

- Performance: roughly closes the gap to pypdevs's `SchedulerHS` on
  DEVStone-style workloads. Beats xdevs by virtue of avoiding xdevs's
  per-tick `min()` linear scan over processors.
- Correctness: confluent transitions match the rest of the ecosystem.
  The cross-engine HI / HO transition-count discrepancy noted in
  `benchmark/results/BASELINE.md` goes away.
- Architectural cleanliness: `schedule()` shrinks from a 70-line nested
  loop with a dirty flag and an interleaved firing order into four
  named phases. Easier to reason about for future contributors.

The cost is real — semantics changes, even with backwards-compatibility
shims, deserve a careful release note. But the structure follows the
DEVS textbook, which is what the rest of the Python-DEVS ecosystem also
follows. Treat it as bringing pyjevsim's abstract simulator into line
with the standard, with a free performance win on the way.
