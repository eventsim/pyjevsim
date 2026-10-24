# Measurement evidence, October 2026

Raw records behind the October 2026 engine work (#41, #42, #44) and the
PythonPDEVS ceiling study, kept so that the figures quoted in those pull
requests, in `CHANGELOG.md` and in `benchmark/results/COMPARE-2026-10-22.md`
can be traced back to data. The files are copied unchanged from the working
directories they were produced in; the drivers still name those directories
(`D:/development/pyjevsim/.claude/worktrees/...` and a scratch `S` argument)
and will not run as they stand.

All runs: Windows 11, CPython 3.14.0, Intel i7-12700. No other Python
version or platform was measured.

| File | What it is | Belongs to |
|---|---|---|
| `round2/all.json` | Round-2 optimisation campaign: profile of the hotspots per workload, the trace oracle's description and self-check, the review of each of five candidates, the serial and stacked timings, and the recommendation. Base is `b447f6f` (#41's branch on `9a2b0d2`); the stacked branch was `fb9bf10`. | #42 (merged as `8135542`); #41 for the base figures |
| `round2/bench_stacked.py` | Interleaved base/stacked/base DEVStone timing driver (7 repetitions, minimum of each) that produced the stacked ratios in `round2/all.json`. | #42 |
| `ceiling/all.json` | PythonPDEVS ceiling study: per-transition anatomy of both engines, the profile gap breakdown, the optimisation ladder (steps, best API-preserving and opt-in ratios), and an adversarial verification of the verdict. | Study; ladder steps 1, 5 and 9 became #44 |
| `ceiling/verdict.md` | The study's written verdict (Korean). | Study |
| `round3/dense_ab.py` | Interleaved main/candidate dense DEVStone comparison through `benchmark/run_compare.py`, pyjevsim against PythonPDEVS, fresh process per run. | #44 |
| `round3/dense_ab_HI1010_LI1010.json`, `round3/dense_ab_HO66.json` | Raw transitions per second of each run of `dense_ab.py` (HI 10x10, LI 10x10, HO 6x6; 7 rounds). | #44 |
| `round3/sparse_ab.py` | Interleaved main/candidate comparison through `benchmark/run_sparse.py`. | #44 |
| `round3/idle_driver.py` | Idle-heavy V_TIME driver: 10,000 passive models plus a few active ping-pong pairs. | #44 |
| `round3/wall_ab.py` | Interleaved main/candidate wall-time driver for `idle_driver.py` and the bank example (`tools/oracle/bank_driver.py`). | #44 |

Not kept here:

- The full trace-oracle digests of these rounds (about 5.3 MB each, with
  multi-megabyte trace sidecars) are over the 2 MB limit for this directory.
  `tools/oracle/golden/v2.2.0.json` holds the per-scenario hashes instead;
  the base digest those rounds were compared against (taken at `b447f6f`)
  matches it in every scenario (see `tools/oracle/README.md`).
- The trace oracle and `bank_driver.py` themselves now live in
  `tools/oracle/`.

Paths inside these files were written by the measurement scripts on the
maintainer's machine. They have been replaced with `<scratchpad>` (the
session's scratch directory) and `<worktree:NAME>` (a temporary git
worktree); files under those paths that are not listed above were not
kept.
