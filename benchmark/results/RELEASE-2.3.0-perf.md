# pyjevsim 2.3.0 performance by interpreter (roadmap INF-6)

This record measures the 2.3.0 release candidate's engine against 2.2.0 on
CPython 3.10 to 3.14 with the standard suite (`benchmark/suite.py`, W1 to
W7). It also measures main with only #41 against 2.2.0 on 3.10, 3.12 and
3.14, to show how much of the gain comes from the #41 counter fix. All runs
were made on 2026-10-24 between 11:36 and 13:04 +09:00 on one Windows
desktop that other jobs were also using. Read [Caveats](#caveats) before
quoting a number.

## What was compared

| side | commit | contents |
|---|---|---|
| base | `9a2b0d22da75c3e3b488ce96b392c957a8784454` (`9a2b0d2`) | v2.2.0 plus docs (main before #41) |
| fix41 | `f14050be671997481efe2b3f889c4efa53435f78` (`f14050b`) | `9a2b0d2` plus #41 only (`SystemObject` counter fix) |
| cand | `cba37cc44c74be5b292123f2c27e823041013130` (`cba37cc`) | main: #41, #42, #44, #47, #48, #49, #50 (the 2.3.0 release candidate's engine) |

Each side is a `git archive` export of its commit. All three sit in one
directory on the same drive (under the Windows temp directory), so file
system location does not skew W6 import time. The harness (`benchmark/` and
the child runner) came from the suite checkout at `42d7760` (PR #51) for
every run; only `pyjevsim` and, for W5, `examples` came from the export
under test. The suite refuses a run whose `pyjevsim` or `examples` resolves
outside the export.

## Environment

| item | value |
|---|---|
| host | 12th Gen Intel Core i7-12700 (8P + 4E, 20 logical CPUs), 64 GB RAM |
| OS | Windows 11 Education 10.0.26300 |
| suite | `benchmark/suite.py` at `42d7760`, parent run with system CPython 3.14.0 |
| power throttling | EcoQoS opt-out on (the default): the parent opted out, and every child ran with `power_opt_out: true` (W6 runs are bare `python -E -c` processes and do not record the field) |
| pinning | none |
| environment variables | `MSYS_NO_PATHCONV=1`, `PYTHONIOENCODING=utf-8` |
| execution | one batch at a time, one child process at a time |

Each interpreter had its own virtual environment, created with uv 0.11.14
(`uv venv --python <version>`), with dill and PyYAML installed by
`uv pip install dill pyyaml`. The same dill release satisfies both sides'
requirements: `dill>=0.3.6` on 2.2.0, and on the candidate the
per-Python minimums in `pyproject.toml` (0.3.6 for 3.10 up to 0.4.1 for
3.14). PyYAML is imported only by the bank example's scripts
(`examples/banksim/runner.py` on the candidate, `banksim_classic.py` on
2.2.0). W5 imports only the model package (`examples.banksim.model`), so
it does not need PyYAML. It was installed anyway so that every environment
can run the examples.

| interpreter | build | source | dill | PyYAML |
|---|---|---|---|---|
| CPython 3.10.20 | MSC v.1944 64 bit (AMD64) | uv-managed (`uv python install 3.10`) | 0.4.1 | 6.0.3 |
| CPython 3.11.15 | MSC v.1944 64 bit (AMD64) | uv-managed | 0.4.1 | 6.0.3 |
| CPython 3.12.13 | MSC v.1944 64 bit (AMD64) | uv-managed | 0.4.1 | 6.0.3 |
| CPython 3.13.13 | MSC v.1944 64 bit (AMD64) | uv-managed | 0.4.1 | 6.0.3 |
| CPython 3.14.0 | MSC v.1944 64 bit (AMD64) | python.org installer (`C:\Python314`) | 0.4.1 | 6.0.3 |

All are GIL builds.

## Protocol

* `python -m benchmark.suite --base <base> --cand <cand|fix41> --rounds N
  --workloads ... --python <venv python> --out <json> --markdown`, run from
  the suite checkout, with the default single warm-up run per workload and
  side and the default 5% noise floor.
* base against cand: W1 to W7, 10 rounds per interpreter. base against
  fix41: W1, W3 and W5, 5 rounds, on 3.10, 3.12 and 3.14.
* Machine load is the mean of five 2 s samples of
  `\Processor(_Total)\% Processor Time`, taken before and after each batch.
  When the reading before a batch was above 25%, the batch waited and
  re-read every 30 s for up to 5 minutes, then started anyway.
* In every batch, every workload had matching parity keys on both sides.
  No workload was `REFUSED` or `FAILED`, and every suite exit status was 0.
* Other jobs held the machine at 53-69% load during three base-against-fix41
  batches and the 3.14 base-against-cand batch. Those four batches were
  repeated afterwards, with a wait of up to 15 minutes for the load to drop
  below 25%. The tables below use the repeats (`*-rerun.json`). The loaded
  runs are kept and listed under [Loaded runs](#loaded-runs).

## How to read the cells

The suite reports `cand/base`. These tables give the inverse, the speed-up
`base time / cand time`, so a value above 1 means 2.3.0 is faster. Each
cell is

`ratio of minimums [median of the per-round paired ratios; lowest-highest paired ratio]`

The ratio of minimums is `min(base) / min(cand)` over all rounds, and a
paired ratio is `base / cand` for the two runs of one round. W1 to W5 and
W7 measure simulation time only (`sim_s`); model build is excluded. W6
measures import time (`import_s`), import plus `SysExecutor(1)`
(`startup_s`) and the whole bare process (`process_s`).

## 2.3.0 against 2.2.0, 10 rounds

| workload | CPython 3.10 | CPython 3.11 | CPython 3.12 | CPython 3.13 | CPython 3.14 |
|---|---:|---:|---:|---:|---:|
| W1 DEVStone HI 10x10, 100 seeds | 1.58x [1.61x; 1.29-1.74] | 1.90x [1.84x; 1.62-2.10] | 1.88x [1.89x; 1.71-1.93] | 2.39x [2.38x; 2.17-2.93] | 2.33x [2.33x; 2.18-2.52] |
| W2 DEVStone LI 10x10, 1000 seeds | 1.59x [1.63x; 1.54-1.74] | 1.80x [1.81x; 1.67-1.95] | 1.83x [1.85x; 1.72-2.00] | 2.55x [2.51x; 2.36-2.85] | 2.52x [2.50x; 2.35-2.62] |
| W3 sparse generator to sink | 1.63x [1.70x; 1.50-1.96] | 1.85x [1.85x; 1.73-2.01] | 1.90x [1.83x; 1.76-1.98] | 2.20x [2.13x; 1.99-2.26] | 2.11x [2.05x; 1.94-2.33] |
| W4 idle-heavy | 1.39x [1.44x; 1.33-1.56] | 1.60x [1.58x; 1.41-2.06] | 1.49x [1.51x; 1.22-1.59] | 2.02x [2.02x; 1.98-2.08] | 1.95x [2.06x; 1.81-2.25] |
| W5 bank example | 1.47x [1.49x; 1.29-1.61] | 1.54x [1.57x; 1.48-1.71] | 1.55x [1.57x; 1.44-1.81] | 1.71x [1.70x; 1.57-1.76] | 1.79x [1.77x; 1.66-2.14] |
| W6 import_s | 4.55x [4.80x; 3.91-7.82] | 4.50x [4.47x; 3.84-5.42] | 4.96x [5.16x; 4.07-5.59] | 7.28x [6.78x; 5.86-7.28] | 4.59x [4.00x; 3.71-5.87] |
| W6 startup_s | 4.55x [4.79x; 3.90-7.81] | 4.49x [4.47x; 3.84-5.41] | 4.95x [5.16x; 4.06-5.59] | 7.27x [6.77x; 5.86-7.27] | 4.58x [4.00x; 3.71-5.86] |
| W6 process_s | 2.28x [2.29x; 1.81-11.42] | 2.06x [2.00x; 1.81-2.44] | 2.20x [2.29x; 2.08-2.43] | 2.74x [2.74x; 2.49-3.00] | 2.05x [1.93x; 1.53-2.37] |
| W7 W1 under SnapshotExecutor | 1.37x [1.36x; 1.25-1.49] | 1.58x [1.55x; 1.45-2.08] | 1.60x [1.60x; 1.48-1.94] | 2.14x [2.12x; 1.94-2.44] | 1.96x [1.94x; 1.88-2.11] |

The 3.14 column is the repeated batch (`py3.14-base-vs-cand-rerun.json`).

Minimum times in milliseconds, `base / cand`:

| workload | CPython 3.10 | CPython 3.11 | CPython 3.12 | CPython 3.13 | CPython 3.14 |
|---|---:|---:|---:|---:|---:|
| W1 | 123.4 / 77.9 | 105.3 / 55.5 | 90.6 / 48.3 | 112.9 / 47.1 | 120.8 / 51.8 |
| W2 | 279.0 / 175.1 | 216.9 / 120.6 | 191.5 / 104.5 | 258.0 / 101.0 | 272.2 / 108.0 |
| W3 | 133.3 / 81.9 | 109.3 / 59.1 | 100.8 / 53.1 | 113.3 / 51.6 | 118.6 / 56.1 |
| W4 | 26.6 / 19.2 | 19.9 / 12.4 | 17.2 / 11.5 | 22.6 / 11.2 | 23.7 / 12.1 |
| W5 | 202.7 / 138.1 | 151.2 / 98.2 | 139.1 / 89.7 | 151.4 / 88.5 | 153.5 / 86.0 |
| W6 import_s | 428.8 / 94.3 | 174.7 / 38.8 | 205.2 / 41.4 | 297.0 / 40.8 | 127.7 / 27.8 |
| W6 startup_s | 428.9 / 94.3 | 174.8 / 38.9 | 205.3 / 41.5 | 297.1 / 40.8 | 127.8 / 27.9 |
| W6 process_s | 574.2 / 251.8 | 235.1 / 114.1 | 269.8 / 122.4 | 382.9 / 139.5 | 194.9 / 94.9 |
| W7 | 182.7 / 133.1 | 143.0 / 90.5 | 112.7 / 70.7 | 141.0 / 66.0 | 141.5 / 72.1 |

What the numbers show:

* 2.3.0 is faster than 2.2.0 on every workload and every interpreter. The
  lowest paired ratio of any engine workload, 1.22x for W4 on 3.12, is far
  outside the 5% noise floor. It is also outside the worst case of the
  loaded A/A runs in `docs/source/benchmark.rst`, where identical code read
  up to 18% apart.
* The engine workloads (W1 to W5, W7) gain least on 3.10 (1.37-1.63x), more
  on 3.11 and 3.12 (1.49-1.90x), and most on 3.13 and 3.14 (1.71-2.55x).
  2.2.0 runs W1 to W4 slower on 3.13 and 3.14 than on 3.12 (W1: 112.9 and
  120.8 ms against 90.6 ms). 2.3.0 runs them in about the same time on 3.12
  to 3.14 (W1: 47.1-51.8 ms). The #41 attribution below fits this: the
  counter fix is worth most on the newer interpreters.
* W6: the candidate imports in 28-94 ms, against 128-429 ms for 2.2.0. In
  2.2.0, `pyjevsim/snapshot_executor.py` imports `dill` at module level,
  and `import pyjevsim` loads that module (through
  `snapshot_factory.py`). The candidate imports `dill` only inside
  `SnapshotExecutor.model_dump`. After `import pyjevsim`, `dill` is in
  `sys.modules` on 2.2.0 and absent on the candidate (checked on 3.12).
  The import ratio therefore
  depends mostly on how long `dill` takes to import on each interpreter.
  The 3.10 `process_s` spread (up to 11.42x) comes from one slow base
  process in round 1.
* W7 does not compare like with like; see the caveat on `con_trans` below.

## The #41 share: main with only #41 against 2.2.0, 5 rounds

| workload | CPython 3.10 | CPython 3.12 | CPython 3.14 |
|---|---:|---:|---:|
| W1 | 1.14x [1.12x; 1.08-1.16] | 1.43x [1.43x; 1.39-1.46] | 1.89x [1.89x; 1.47-2.35] |
| W3 | 1.22x [1.17x; 1.12-1.23] | 1.43x [1.46x; 1.35-1.53] | 1.61x [1.72x; 1.61-1.81] |
| W5 | 1.20x [1.18x; 1.09-1.24] | 1.31x [1.31x; 1.29-1.37] | 1.37x [1.48x; 1.19-1.75] |

Minimum times in milliseconds, `base / fix41`:

| workload | CPython 3.10 | CPython 3.12 | CPython 3.14 |
|---|---:|---:|---:|
| W1 | 124.7 / 109.8 | 91.0 / 63.5 | 123.3 / 65.1 |
| W3 | 136.7 / 111.7 | 101.1 / 70.7 | 118.5 / 73.7 |
| W5 | 201.3 / 167.5 | 138.2 / 105.1 | 151.2 / 110.0 |

The next table puts the #41 speed-up beside the whole 2.3.0 speed-up
(ratios of minimums). The percentage is the #41 share of the whole on a log
scale, `ln(fix41 speed-up) / ln(2.3.0 speed-up)`:

| workload | CPython 3.10 | CPython 3.12 | CPython 3.14 |
|---|---:|---:|---:|
| W1 | 1.14x of 1.58x (28%) | 1.43x of 1.88x (57%) | 1.89x of 2.33x (75%) |
| W3 | 1.22x of 1.63x (41%) | 1.43x of 1.90x (56%) | 1.61x of 2.11x (64%) |
| W5 | 1.20x of 1.47x (48%) | 1.31x of 1.55x (62%) | 1.37x of 1.79x (55%) |

On 3.14, #41 alone accounts for most of the W1 and W3 gain. On 3.10, the
other changes since 2.2.0 (#42 to #50) account for most of it. The share is
approximate. The two speed-ups come from different batches (10 and 5
rounds, run about an hour apart), so each carries its own noise. If each
ratio is a few percent off, the share can move by several points.

## Machine load per batch

Each row gives the mean `% Processor Time` over 10 s before and after the
batch, the time the batch waited for the load to drop, and the suite's exit
status.

| batch | start (+09:00) | load before | waited | load after | status |
|---|---|---:|---:|---:|---:|
| 3.10 base vs cand | 11:36:21 | 24.8% | 0 s | 32.3% | 0 |
| 3.11 base vs cand | 11:46:01 | 25.5% | 300 s (limit) | 32.0% | 0 |
| 3.12 base vs cand | 11:47:57 | 23.3% | 30 s | 26.4% | 0 |
| 3.13 base vs cand | 11:56:22 | 26.9% | 300 s (limit) | 25.2% | 0 |
| 3.14 base vs cand (loaded, superseded) | 12:05:07 | 68.7% | 300 s (limit) | 68.3% | 0 |
| 3.10 base vs fix41 (loaded, superseded) | 12:15:19 | 57.6% | 300 s (limit) | 53.2% | 0 |
| 3.12 base vs fix41 (loaded, superseded) | 12:23:38 | 54.9% | 300 s (limit) | 54.7% | 0 |
| 3.14 base vs fix41 (loaded, superseded) | 12:31:47 | 53.2% | 300 s (limit) | 55.2% | 0 |
| 3.14 base vs cand, repeat | 12:45:21 | 24.7% | 540 s | 28.4% | 0 |
| 3.10 base vs fix41, repeat | 12:51:38 | 24.1% | 210 s | 26.0% | 0 |
| 3.12 base vs fix41, repeat | 12:55:30 | 24.2% | 120 s | 23.9% | 0 |
| 3.14 base vs fix41, repeat | 13:03:58 | 23.5% | 330 s | 36.3% | 0 |

The load never fell to the 10-20% of the 2026-10-22 record. Desktop
applications that stayed busy throughout supplied about 25%, and from about
12:00 other jobs' Python processes added 30-45 points more. Two batches
(3.11 and 3.13) started slightly above 25% after the 5-minute wait.

### Loaded runs

These are the superseded batches, kept for completeness. They show the same
direction, but their paired ratios spread far wider, from 0.88x to 3.87x.
Their ratios of minimums differ from the repeats by up to 0.46x (3.10 W3
with #41: 1.68x loaded, 1.22x repeated). Do not quote them.

| workload | 3.14 base vs cand | 3.10 base vs fix41 | 3.12 base vs fix41 | 3.14 base vs fix41 |
|---|---:|---:|---:|---:|
| W1 | 2.66x [2.56x; 1.86-3.87] | 1.39x [1.13x; 1.11-1.49] | 1.26x [1.39x; 0.88-1.67] | 1.97x [1.99x; 1.58-2.49] |
| W2 | 2.42x [2.42x; 2.14-3.35] | | | |
| W3 | 1.91x [2.14x; 1.29-3.42] | 1.68x [1.44x; 1.15-1.68] | 1.84x [1.49x; 1.26-2.10] | 1.76x [1.86x; 1.38-2.22] |
| W4 | 1.95x [1.84x; 1.62-3.60] | | | |
| W5 | 2.11x [1.86x; 1.55-2.47] | 0.99x [1.22x; 0.96-1.44] | 1.38x [1.40x; 1.30-1.50] | 1.50x [1.50x; 1.09-1.97] |
| W6 import_s | 4.62x [4.43x; 3.51-5.75] | | | |
| W6 startup_s | 4.62x [4.42x; 3.50-5.74] | | | |
| W6 process_s | 2.09x [2.11x; 1.82-2.59] | | | |
| W7 | 2.48x [2.10x; 1.59-2.72] | | | |

## Caveats

* **Shared, busy machine.** Every batch ran with 23-37% background load
  from other work, above the quiet-machine conditions the 5% floor assumes.
  In the A/A runs of `docs/source/benchmark.rst`, ten unpinned rounds held
  identical code within 5% at 30-45% load. Every 2.3.0 ratio here is well
  beyond that, so the direction and rough size are safe; the second decimal
  is not. Quote "about 1.6x on 3.10 to about 2.4x on 3.14", not a precise
  figure. No A/A run was made on the day; the floor comes from the
  2026-10-23 record.
* **Windows only.** All numbers come from Windows 11 on one i7-12700. Linux
  and macOS were not measured. Absolute times and per-interpreter ratios
  may differ on them. For example, import time depends on the file system,
  and the EcoQoS opt-out exists only on Windows.
* **Interpreter builds differ in origin.** 3.10 to 3.13 are uv-managed
  (python-build-standalone) builds, and 3.14.0 is the python.org installer
  build. Compare ratios across interpreters, not absolute times.
* **Interpreter recorded in the JSON.** In every file, the suite's
  `environment.python` field holds the parent process's interpreter
  (3.14.0). The children ran the interpreter named by
  `environment.executable` (the venv path), whose version is in the
  environment table above.
* **W7 compares two different `con_trans` paths.** 2.2.0 has no
  `SnapshotExecutor.con_trans`, so the suite adds its shim on the base side
  (`con_trans_shim: true`, 32,400 confluent transitions per run, about 80%
  of the internal transitions). The candidate uses its own `con_trans`
  from #47 (`con_trans_shim: false`). W7 therefore includes the difference
  between the shim and the real method as well as the engine changes.
* **W6 mostly measures the `dill` import.** It reflects a packaging change
  (the lazy `dill` import), not the simulation engine, and it depends on
  the installed `dill` version (0.4.1 everywhere here).
* **The #41 share is approximate.** It combines two speed-ups from separate
  batches (see above), and it covers only three workloads on three
  interpreters.
* **Fewer rounds for #41.** As planned, the base-against-fix41 batches ran
  5 rounds. The loaded A/A runs showed that 5 rounds do not always hold a
  5% floor, but the #41 effects measured here (1.14-1.89x) are far larger
  than that.
* **The 2.3.0 side is the release candidate's engine, not a tagged
  release.** `cba37cc` is main at the time of measurement. Changes made
  after it and before the tag are not covered.

## Files

`benchmark/results/release-2.3.0/` holds the suite's `--out` JSON for every
batch, including the superseded loaded runs, and the two load logs:

| file | batch |
|---|---|
| `py3.10-base-vs-cand.json` ... `py3.13-base-vs-cand.json` | base vs cand, W1-W7, 10 rounds |
| `py3.14-base-vs-cand-rerun.json` | base vs cand on 3.14, repeat (used above) |
| `py3.14-base-vs-cand.json` | base vs cand on 3.14, loaded (superseded) |
| `py3.{10,12,14}-base-vs-fix41-rerun.json` | base vs fix41, W1/W3/W5, 5 rounds, repeat (used above) |
| `py3.{10,12,14}-base-vs-fix41.json` | base vs fix41, loaded (superseded) |
| `loads.tsv`, `loads-rerun.tsv` | load before and after each batch, wait and exit status |

Absolute paths in these files were replaced with `<scratchpad>`, the
session's scratch directory. The exports lived under it at
`phaseA/inf6b/{base,fix41,cand}` and the virtual environments at
`phaseA/inf6b/venvs/py3.N`. Each run record keeps its times, parity key,
round, position and `power_opt_out`.

To reproduce one batch, export the commits and run the suite from a
checkout that contains it:

```console
$ git archive 9a2b0d2 | tar -x -C ../base
$ git archive cba37cc | tar -x -C ../cand
$ python -m benchmark.suite --base ../base --cand ../cand --rounds 10 \
    --workloads W1,W2,W3,W4,W5,W6,W7 --python <venv>/Scripts/python.exe \
    --out py3.N-base-vs-cand.json --markdown
```
