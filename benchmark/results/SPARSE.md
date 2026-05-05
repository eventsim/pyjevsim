# Sparse-time Baseline (cross-engine)

Date captured: 2026-05-05 (re-captured after V_TIME jump-scheduling landed).
Generator: `python3 -m benchmark.run_sparse --output benchmark/results/sparse.csv`
Best of three runs.

## Setup

Tiny topology (1 generator → 1 sink) with the work held constant at
**100 events**. Only the inter-event simulated period changes — we walk
the period from 1 tick up to 1000 ticks. Each engine should ideally show
*the same* wall time across all periods, because the actual transition
work is identical; any per-tick overhead in the executor's main loop is
what shows up as a slowdown when period grows.

## Results (current, after all sparse-time fast-paths)

| period | pyjevsim | xdevs | pypdevs | reference |
|--------|----------|-------|---------|-----------|
| 1      |   393 k  | 449 k |   760 k |  1.71 M   |
| 10     |   410 k  | 462 k |   811 k |  1.69 M   |
| 100    |   412 k  | 455 k |   802 k |  1.72 M   |
| 1000   |   396 k  | 460 k |   785 k |  1.63 M   |

Wall-clock simulation time (`sim_s`):

| period | pyjevsim | xdevs   | pypdevs | reference |
|--------|----------|---------|---------|-----------|
| 1      |  0.5 ms  |  0.4 ms |  0.3 ms |   0.1 ms  |
| 10     |  0.5 ms  |  0.4 ms |  0.2 ms |   0.1 ms  |
| 100    |  0.5 ms  |  0.4 ms |  0.3 ms |   0.1 ms  |
| 1000   |  0.5 ms  |  0.4 ms |  0.3 ms |   0.1 ms  |

## Result

**pyjevsim is now period-independent**, like xdevs / pypdevs / reference.
Throughput stays in the 280–290 k tr/s band whether the inter-event gap is
1 tick or 1000 ticks. The dramatic 230× collapse seen before the fix is
gone.

## Pre-fix numbers (for comparison)

| period | pyjevsim before | pyjevsim after | speedup |
|--------|-----------------|----------------|---------|
| 1      |    264 k tr/s   |    279 k tr/s  |  ~1×    |
| 10     |     74 k tr/s   |    282 k tr/s  |  3.8×   |
| 100    |      9 k tr/s   |    285 k tr/s  |  31×    |
| 1000   |      1 k tr/s   |    290 k tr/s  |  263×   |

For period=1000 the wall time dropped from 184 ms → 0.7 ms.

## What changed

`SysExecutor.schedule()` (`pyjevsim/system_executor.py`) now consults a
private `_peek_next_event_time()` helper and, in V_TIME mode, jumps
`global_time` directly to the next scheduled event (FEL head, external
input queue head, or waiting-creation queue head — whichever is smallest),
clamped at `target_time`. R_TIME and HLA_TIME are unchanged.

The change is the implementation of plan item **T1.1**.

## Reproducing

```
python3 -m benchmark.run_sparse \
    --periods 1 10 100 1000 --count 100 --repeat 3 \
    --output benchmark/results/sparse.csv
```

Per-row data is in `sparse.csv`. The runner accepts `--engines` to
restrict the comparison set and `--period N` for a single configuration.

## Reproducing

```
python3 -m benchmark.run_sparse \
    --periods 1 10 100 1000 --count 100 --repeat 3 \
    --output benchmark/results/sparse.csv
```

Per-row data is in `sparse.csv`. The runner accepts `--engines` to
restrict the comparison set and `--period N` for a single configuration.
