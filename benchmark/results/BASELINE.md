# Cross-engine DEVStone record

This table was captured on 2026-05-05 with the comparison runner and a grid
that also included the 8 × 8 and 10 × 10 HI cases. Each cell is the best of
three runs. The benchmark disabled synthetic CPU work
(`int_cycles == ext_cycles == 0`) and therefore emphasizes executor and
routing overhead. The exact invocation and generated CSV were not retained,
so this table is a historical record rather than a reproducible release
result.

| Variant | depth × width | pyjevsim tr/s | xdevs tr/s | pypdevs tr/s | reference tr/s |
|---|---:|---:|---:|---:|---:|
| LI | 2 × 2 | 121 k | 343 k | 307 k | 911 k |
| LI | 4 × 4 | 344 k | 705 k | 802 k | 1.69 M |
| LI | 6 × 6 | 500 k | 976 k | 1.13 M | 2.16 M |
| HI | 2 × 2 | 143 k | 389 k | 348 k | 1.19 M |
| HI | 4 × 4 | 410 k | 554 k | 901 k | 2.00 M |
| HI | 6 × 6 | 616 k | 662 k | 1.34 M | 2.36 M |
| HI | 8 × 8 | 715 k | 738 k | 1.73 M | 2.69 M |
| HI | 10 × 10 | 844 k | 771 k | 2.00 M | 2.70 M |
| HO | 2 × 2 | 148 k | 620 k | 368 k | 1.19 M |
| HO | 4 × 4 | 404 k | 729 k | 908 k | 1.95 M |
| HO | 6 × 6 | 623 k | 800 k | 1.32 M | 2.31 M |

The measurements apply only to the listed configurations and capture date.
They should not be read as a general ranking of the engines. In particular,
topology, transition count, Python version, dependency versions, host load,
and timer resolution can all change the reported throughput.

## Engines used

| Engine | Recorded version or source |
|---|---|
| pyjevsim | repository `HEAD` at capture time; the commit was not recorded |
| xdevs.py | 3.0.0 |
| PythonPDEVS | 2.4.1 from the `capocchi/PythonPDEVS` repository, with the compatibility edits below |
| reference | `benchmark/engines/reference/` in this repository |

PythonPDEVS required three local Python 3 compatibility edits for the run:

1. change `from schedulers.schedulerAuto` in `pypdevs/minimal.py` to the
   absolute import `from pypdevs.schedulers.schedulerAuto`;
2. change `transitioning.iteritems()` to `transitioning.items()`; and
3. add the scheduler's infinite-time sentinel to the empty heap in
   `pypdevs/schedulers/schedulerHS.py`.

## Run a new comparison

Install the engines you want to compare, then check which adapters are
available:

```bash
python -m benchmark.run_compare --list-engines
```

Run the default grid and save the per-row metadata:

```bash
python -m benchmark.run_compare --repeat 3 \
  --output benchmark/results/baseline.csv
```

Record the pyjevsim commit, Python and engine versions, operating system, CPU,
and raw CSV with any result intended for publication. Compare transition
counts as well as elapsed time; throughput values are not comparable when the
engines perform different transition work.
