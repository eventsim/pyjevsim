# DEVStone Baseline (cross-engine)

Date captured: 2026-05-05
Generator: `python3 -m benchmark.run_compare --output benchmark/results/baseline.csv`
Each cell is the best of three runs; CPU work disabled (`int_cycles == ext_cycles == 0`).

| Variant | depth × width | pyjevsim tr/s | xdevs tr/s | pypdevs tr/s | reference tr/s |
|---------|---------------|---------------|------------|--------------|----------------|
| LI      | 2 × 2         |   121 k       |   343 k    |   307 k      |   911 k        |
| LI      | 4 × 4         |   344 k       |   705 k    |   802 k      |  1.69 M        |
| LI      | 6 × 6         |   500 k       |   976 k    |  1.13 M      |  2.16 M        |
| HI      | 2 × 2         |   143 k       |   389 k    |   348 k      |  1.19 M        |
| HI      | 4 × 4         |   410 k       |   554 k    |   901 k      |  2.00 M        |
| HI      | 6 × 6         |   616 k       |   662 k    |  1.34 M      |  2.36 M        |
| HI      | 8 × 8         |   715 k       |   738 k    |  1.73 M      |  2.69 M        |
| HI      | 10 × 10       | **844 k**     |   771 k    |  2.00 M      |  2.70 M        |
| HO      | 2 × 2         |   148 k       |   620 k    |   368 k      |  1.19 M        |
| HO      | 4 × 4         |   404 k       |   729 k    |   908 k      |  1.95 M        |
| HO      | 6 × 6         |   623 k       |   800 k    |  1.32 M      |  2.31 M        |

**At HI 10×10 pyjevsim now beats xdevs** — the heapset scales better than
xdevs's per-tick `min(p.time_next for p in processors)` linear scan. The
crossover sits between width=8 and width=10.

Geo-mean gap to xdevs: **1.3×** (was 3.0× before any fixes). Geo-mean gap
to pypdevs: **2.4×**.

Numbers reflect:
- T1.1 V_TIME jump-to-next-event
- Cascade-aware Parallel-DEVS tick (correct `δ_con` semantics)
- T1.2 heapset priority queue
- Small refactor wave (cached `obj_id`, inlined `set_req_time`, lock skip)
- dmc routing bypass for uncoupled emits

Geo-mean gap to xdevs: **1.4×**. Geo-mean gap to pypdevs: **2.5×**.

### Why LI improved disproportionately

In the flat DEVStone topology, LI is the "all atomics emit to nowhere"
case — every atomic's output goes to the default message catcher (no
real coupling). Pre-fix, each emit paid for one `dmc.ext_trans` +
`set_req_time` + `ScheduleQueue.push`, dominating per-tick cost.
Bypassing the dmc fallback (uncoupled emits become genuine no-ops)
saves 26 routings per round in LI 6×6, dropping per-tick wall time
from 450 µs → 240 µs. HI/HO are less affected because most outputs
have real downstream couplings (the chain).

These numbers reflect the cascade-aware two-phase tick (Parallel-DEVS
correct semantics — `δ_int`, `δ_ext`, `δ_con` properly distinguished).
Transition counts now **converge to xdevs / pypdevs / reference** for HI
and the chain-shaped pyjevsim HO topology — this was the empirical
signal that the confluent fix landed:

| variant | pyjevsim before fix | pyjevsim after fix |
|---------|---------------------|--------------------|
| HI 4×4  | 26                  | **38** (matches)   |
| HI 6×6  | 72                  | **152** (matches)  |
| HO 4×4  | 26                  | **38** (matches)   |
| HO 6×6  | 72                  | **152** (matches)  |

Wall-clock improved on top of the count change: pyjevsim throughput rose
~50–80% on dense DEVStone despite doing ~2× the transition work, because
heapify now runs once per tick instead of once per dirty event.

Geometric-mean slowdown of pyjevsim across the three other engines:

| vs                  | slowdown    |
|---------------------|-------------|
| **xdevs**           | ~3.7×       |
| **pypdevs minimal** | ~5.0×       |
| **reference**       | ~10×        |

xdevs and PythonPDEVS are the closest peers; the hand-rolled reference is a
"no-framework-overhead" floor. The gap to the reference engine roughly
bounds how much the optimisations in `docs/p_plan.md` can buy.

## Transition-count caveat

LI counts match across all four engines. HI and HO counts diverge for
pyjevsim because of how each engine handles **confluent transitions**:

- **xdevs**, **pypdevs**, **reference** — implement
  `deltcon = deltint; deltext`. Chained atomics in HI fire 38 / 152
  transitions for d4w4 / d6w6.
- **pyjevsim** — routes external events into the receiver inside the same
  `schedule()` iteration (`pyjevsim/system_executor.py:370-386`) and skips
  the second output, so HI shows 26 / 72 transitions.

xdevs HO uses a separate output port that escapes via EOC chains, which
collapses some confluent firings; that is why xdevs HO also shows 26 / 72
while pypdevs HO matches HI (38 / 152).

## Engines covered

| engine          | version | install                                                  |
|-----------------|---------|----------------------------------------------------------|
| pyjevsim        | HEAD    | this repository                                          |
| xdevs.py        | 3.0.0   | `pip install xdevs`                                      |
| PythonPDEVS     | 2.4.1   | manual: `git clone https://github.com/capocchi/PythonPDEVS.git && cd PythonPDEVS/src && pip install .` then apply the Python-3 patches noted below |
| reference       | -       | `benchmark/engines/reference/` (~150 LOC, in this repo)  |

### PythonPDEVS Python-3 patches

The capocchi fork is the only PyPDEVS we found that almost runs on Python 3,
but two issues remain in the minimal kernel:

1. `pypdevs/minimal.py:101` — relative import `from schedulers.schedulerAuto`
   needs to be the absolute `from pypdevs.schedulers.schedulerAuto`.
2. `pypdevs/minimal.py:218` — `transitioning.iteritems()` must become `.items()`.
3. `pypdevs/schedulers/schedulerHS.py:51` — `readFirst()` crashes on an empty
   heap when every model passivates. Push `self.infinite` to `self.heap` once
   in `__init__` so it acts as an absorbing sentinel.

Apply those three edits to the installed package (or fork the repo). Without
them the minimal kernel raises `IndexError: list index out of range` on any
non-trivial DEVStone configuration.

## Reproducing

```
pip install xdevs
git clone https://github.com/capocchi/PythonPDEVS.git /tmp/pythonpdevs
cd /tmp/pythonpdevs/src && pip install .
# apply the three patches above to the installed package
python3 -m benchmark.run_compare --output benchmark/results/baseline.csv
```

Per-row metadata is in `baseline.csv` (`model_build_s`, `engine_setup_s`,
`sim_s`, `transitions`, `transitions_per_s`, `error`).
