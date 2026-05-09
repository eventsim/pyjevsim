# pp_improvement — pyjevsim 2.1 Design

Status: **Draft**, locked decisions only — implementation has not started.
Branch: `pp_improvement` (off `main` at `v2.0.1`).
Target release: **pyjevsim 2.1** (additive, no breaking changes).

> Earlier drafts of this document scoped a 3.0 rewrite (atomic flattening,
> parallel kernel, ensemble runner, 100K-model target). That ambition has
> moved to a separate proprietary engine project (Rust core + multi-language
> bindings). pyjevsim stays the **academic reference implementation**:
> single-process, hierarchical at runtime, snapshot/restore preserved,
> existing user code keeps working.

## 1. Goals

- **Polish-only release.** Modernize boundary validation and add ergonomic helpers without touching the engine architecture or the public model API.
- **Zero migration burden.** All existing user code that runs on 2.0.x runs unchanged on 2.1.
- **Validate at boundaries.** Configuration, snapshot metadata, and (opt-in) message payloads gain pydantic-v2 schemas so misconfigured inputs fail at construction with a clear error, not later with a cryptic one.
- **Quality-of-life features for larger model graphs.** Hierarchical Unix-path names, a registry with glob lookup, and a batch coupling DSL — all purely additive.
- **Set up the conformance contract** for the future proprietary engine: the pydantic schemas added here are exactly what its Python binding will mirror.

## 2. Non-goals

- No `BehaviorModel` / `StructuralModel` / `SysExecutor` API break.
- No atomic flattening, port interning, parallel kernel, ensemble runner, incremental snapshot, Cython, mypyc, or 100K-model target. These belong to the separate proprietary engine project, not pyjevsim.
- No change to V_TIME / R_TIME / HLA_TIME execution-mode semantics.
- No change to the snapshot/restore format or the `dill` dependency.

## 3. Locked decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Pydantic v2 at boundaries only** | `SimulationConfig`, snapshot header, opt-in `TypedMessage[T]`. **Not** on `BehaviorModel` itself — per-instance validation cost would be wasted on the academic-scale workloads pyjevsim targets. |
| 2 | **`__slots__` on hot data classes** | `Executor` family, `MessageDeliverer`, internal `ScheduleQueue` entries. Modest memory + attribute-access win; no API surface change. |
| 3 | **Hierarchical Unix-path names** (`/floor1/queue_47`) are **additive** | Models register under a path; the existing flat `model_map` behavior is preserved. Glob lookup via `fnmatch`. Old `get_entity("name")` lookups still work. |
| 4 | Hierarchical-name validation: per segment `[A-Za-z0-9_.\-]`; `/` only as separator | `fnmatch` glob lookups break on literal `[`, `*`, `?`, `\`. Whitespace and non-ASCII corrupt log output. Fail loudly at registration. |
| 5 | Duplicate-name registration under same parent → **error** | Silent suffix-increment makes mysteries; last-write-wins corrupts. Error names the prior registration site. |
| 6 | **Batch coupling DSL** (`couple`, `fan_in`, `broadcast`) is sugar over `coupling_relation` | Each call expands to N existing `coupling_relation` calls. Old API stays. |
| 7 | **Snapshot / restore unchanged** | Existing `dill`-based machinery keeps the academic "model surgery" use case. No delta tracking, no schema migration. |
| 8 | **Minor version bump: 2.0 → 2.1** | Additive only; no API break. |
| 9 | **Defer Cython / mypyc** | Out of scope for 2.1; revisit only if perf complaints justify it. |
| 10 | **The proprietary engine is a separate project** | Documented elsewhere (TBD `docs/improvements/<engine>_design.md`). pyjevsim 2.1 should stay self-contained and not pre-shape itself for that engine beyond the pydantic schemas (which serve double duty). |

## 4. Phase plan

```
Phase 0  baseline + profile          [done]
            │
            ▼
Phase 1  Pydantic v2 at boundaries   [~3-5 days]
            │
            ▼
Phase 2  __slots__ + hierarchical     [~3-5 days]
         names + registry + DSL
            │
            ▼
Phase 3  Docs + 2.1.0 release        [~1-2 days]
```

### Phase 0 — Baseline + profile *(done)*

- `benchmark/results/pp_baseline/devstone_v2.0.1.csv` captured.
- cProfile of HI 4×4 / 100 events captured (in §7 of this doc).

### Phase 1 — Pydantic v2 at boundaries (~3-5 days)

**Deliverables**:
1. `SimulationConfig(BaseModel)` — validates `time_resolution > 0`, `ex_mode ∈ ExecutionType`, `sim_name` non-empty, `track_uncaught: bool`. `SysExecutor.__init__` accepts either a config object or the old positional kwargs — old call sites work unchanged.
2. `SnapshotHeader(BaseModel)` — sim_name, global_time, model_count, schema_version, created_at. Wraps the JSON-ish header that lives alongside the binary `dill` blob.
3. `TypedMessage[T]` — opt-in: `class MyPayload(BaseModel): user_id: int`; `msg = TypedMessage[MyPayload].new(payload=MyPayload(user_id=42))`. Free-form `SysMessage` with `.insert(anything)` keeps working unchanged.
4. Add `pydantic >= 2.0, < 3` to `pyproject.toml` dependencies.

**Success criterion**:
- Every existing test in `tests/` passes without modification.
- Construction of `SysExecutor(1, ex_mode=ExecutionType.V_TIME)` (old style) and `SysExecutor.from_config(SimulationConfig(...))` (new style) produce identical executors.
- `pip install pyjevsim` installation footprint grows by ≤ 5 MB (pydantic v2 + Rust validator wheel).

### Phase 2 — `__slots__` + naming + registry + DSL (~3-5 days)

**Deliverables**:

| Component | Sketch |
|---|---|
| `__slots__` pass | Add to `Executor`, `BehaviorExecutor`, `StructuralExecutor`, `MessageDeliverer`, internal queue entries. **Skip** `BehaviorModel` and `StructuralModel` themselves so user subclasses aren't constrained. |
| `HierarchicalRegistry` | `dict[str, Executor]` keyed on Unix-path names. Built incrementally as `register_entity` is called. |
| `register_entity(model, name="/path/to/it")` | New optional `name` kwarg with the hierarchical path. If omitted, falls back to current `model.get_name()` flat behavior. |
| `SysExecutor.find(pattern)` | `fnmatch.filter`-based glob lookup. Returns list of executors. Empty list if no match (no exception). |
| `couple(srcs, "out", dsts, "in")` | Zip-couple. Asserts `len(srcs) == len(dsts)`. |
| `fan_in(srcs, "out", dst, "in")` | Many-to-one. |
| `broadcast(src, "out", dsts, "in")` | One-to-many. |

**Success criterion**:
- `tests/` still 40/40 passing.
- New tests: `tests/test_registry.py` (5+ cases), `tests/test_batch_couple.py` (3+ cases per DSL helper), `tests/test_simulation_config.py`.
- A 1000-model smoke test using batch DSL (`tests/test_batch_couple.py::test_1000_zip`) builds and simulates in < 2 s.

### Phase 3 — Docs + release (~1-2 days)

**Deliverables**:
- `README.md`: section on `SimulationConfig`, hierarchical names, batch DSL.
- `docs/source/pyjevsim_quick_start.rst`: append "2.1 ergonomics" section after the existing 2.0 sections.
- `docs/source/pyjevsim_system_executor.rst`: autodoc for `SimulationConfig`, `HierarchicalRegistry`, `SnapshotHeader`.
- New `docs/source/pyjevsim_typed_message.rst` for `TypedMessage[T]`.
- `CHANGELOG.md`: `[2.1.0] — YYYY-MM-DD` block listing additions.
- Bump `pyproject.toml` to `2.1.0`.
- Build, `twine check`, upload to PyPI.

**Success criterion**:
- RTD auto-build succeeds on push.
- `pip install pyjevsim==2.1.0` works on Linux + macOS + Windows.

## 5. API sketches

### 5.1 `SimulationConfig`

```python
from pyjevsim import SimulationConfig, SysExecutor, ExecutionType

# Old style — still works
se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, track_uncaught=True)

# New style — validated at construction
config = SimulationConfig(
    time_resolution=1.0,
    sim_name="bank_sim",
    ex_mode=ExecutionType.V_TIME,
    track_uncaught=True,
)
se = SysExecutor.from_config(config)
```

### 5.2 Hierarchical names and registry

```python
floor1_queue = Queue("queue_47")
se.register_entity(floor1_queue, name="/floor1/queue_47")

floor2_queue = Queue("queue_47")
se.register_entity(floor2_queue, name="/floor2/queue_47")  # OK, different path

# Lookup
se.find("/floor1/queue_47")     # [floor1_queue's executor]
se.find("/floor*/queue_47")     # both queues
se.find("/floor1/*")            # everything under /floor1
se.get_entity("queue_47")       # still works — flat lookup, returns both
```

### 5.3 Batch coupling DSL

```python
from pyjevsim import couple, fan_in, broadcast

gens  = [PEG(f"gen_{i}")  for i in range(100)]
sinks = [Sink(f"sink_{i}") for i in range(100)]
for g in gens:  se.register_entity(g)
for s in sinks: se.register_entity(s)

couple(gens, "process", sinks, "recv")            # 100 individual couplings
fan_in(sinks, "result", aggregator, "in")         # 100 → 1
broadcast(clock, "tick", gens, "tick_in")         # 1 → 100
```

### 5.4 `TypedMessage[T]` (opt-in)

```python
from pydantic import BaseModel
from pyjevsim import TypedMessage, SysMessage

class BankUser(BaseModel):
    user_id: int
    arrival_time: float
    service_time: float

# In a model's output()
def output(self, md):
    msg = TypedMessage[BankUser].new(
        src=self.get_name(),
        dst="user_out",
        payload=BankUser(user_id=42, arrival_time=self.global_time, service_time=3.5),
    )
    md.insert_message(msg)

# In a downstream model's ext_trans()
def ext_trans(self, port, msg):
    user: BankUser = msg.payload   # IDE-typed, validated
```

Free-form `SysMessage(...).insert(anything)` is unchanged.

## 6. Migration from 2.0.x → 2.1

**Zero required changes for existing models or simulation scripts.** All new features are additive:

- Old `SysExecutor(time_resolution, ex_mode=...)` constructor — works.
- Old `register_entity(model)` without `name=` — works (uses `model.get_name()` flat behavior).
- Old `coupling_relation(src, "out", dst, "in")` — works.
- Old `SysMessage(src, dst).insert(anything)` — works.
- Old snapshots written by 2.0.x — restore unchanged in 2.1.

Optional adoption suggestions (recommended in the migration guide but not required):
- Replace `SysExecutor(...)` kwargs with `SimulationConfig(...)` for cleaner construction sites.
- Add `name="/path/to/it"` to `register_entity` calls when you have many models.
- Use `couple` / `fan_in` / `broadcast` instead of for-loops over `coupling_relation`.

## 7. Phase 0 baselines (carried from prior draft)

From `benchmark/results/pp_baseline/devstone_v2.0.1.csv`:

| variant | depth × width | events/s |
|---------|---------------|----------|
| LI | 4 × 4 | 281 k |
| HI | 3 × 3 | 569 k |
| HI | 4 × 4 | 794 k |
| HO | 4 × 4 | 576 k |

cProfile of HI 4×4 / 100 events:
- `system_executor.schedule()`: ~30% exclusive
- `atomic.output()` (user code): 17.5%
- `schedule_queue.push`: 11%
- `behavior_model.con_trans`: 10%

Per-phase **success criterion** for any sequential perf claim: "≥ X% improvement on this baseline." 2.1 is not optimization-driven — these numbers should stay roughly flat. A regression of more than 5% on the headline `events/s` numbers blocks the release.

## 8. Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Adding `pydantic` as a hard dependency bloats install size and adds a Rust-compiled wheel. | Acceptable: pydantic v2 wheels are widely available, ~2-3 MB. If a niche platform lacks a wheel, document the fallback. |
| R2 | `TypedMessage[T]` adoption never catches on; users stay with `SysMessage.insert(...)`. | Acceptable. It's opt-in. The cost of shipping it is small even if it sees no use. |
| R3 | `__slots__` on `Executor` subclasses interacts badly with pickle/dill in obscure cases. | Test against the existing snapshot test suite; revert per-class if snapshots break. |
| R4 | Hierarchical-name validation rejects names that worked in 2.0.x (e.g., names containing `:` or `+`). | Validation only fires on the new `register_entity(model, name="...")` codepath. The old `register_entity(model)` path uses `model.get_name()` and skips validation, so 2.0.x behavior is preserved. |

## 9. Out of scope (explicit)

Punted to the separate proprietary-engine project:
- Atomic flattening
- Port interning to int IDs
- Conservative parallel kernel
- Ensemble / PredictiveRunner
- Incremental snapshot
- 100K-model target
- Cython / mypyc
- Pluggable kernel protocol
- Multi-language bindings
- Declarative class-level state/port schemas (Option A from prior draft)

## 10. Document changelog

| Date | Change |
|------|--------|
| 2026-05-09 (am) | Initial draft — 3.0 rewrite scope (parallel kernel, flattening, ensemble, 100K target, Option A schemas). |
| 2026-05-09 (pm) | Rescoped to 2.1 polish-only. Ambitious work moved to separate proprietary-engine project. Decisions ledger reduced 11 → 10 items; 4 phases reduced to 3. |
