DEVStone Benchmark
==================

Introduction
------------

DEVStone is a synthetic DEVS workload. The implementation under
``benchmark/`` supplies three topologies for measuring executor and routing
costs without application-specific model logic.

Variants
--------

Every variant is built as ``Generator -> level_0 -> level_1 -> ... -> Sink``
where each *level* contains ``width`` ``DEVStoneAtomic`` instances. The
``depth`` parameter controls the number of stacked levels.

- **LI (Low Interconnect)** — one atomic per level participates in the
  forward chain.
- **HI (High Interconnect)** — every atomic in a level receives the level's
  input and feeds the next atomic in the chain.
- **HO (High Output)** — the HI topology plus an ``outx`` port from each
  atomic to the sink.

Layout
------

.. code-block:: text

    benchmark/
    ├── devstone/
    │   ├── atomic.py     # DEVStoneAtomic / DEVStoneGenerator / DEVStoneSink
    │   └── topology.py   # build_devstone(variant, depth, width, ...)
    ├── run_devstone.py   # CLI runner
    ├── suite.py          # standard performance suite (see below)
    ├── workloads/        # the suite's workloads W1-W7 and its child runner
    └── results/          # historical summaries; generated CSVs when requested

Usage
-----

Run a single configuration:

.. code-block:: console

   $ python -m benchmark.run_devstone --variant hi --depth 4 --width 4 --events 100

Run the canonical sweep across LI/HI/HO and persist results to CSV:

.. code-block:: console

   $ python -m benchmark.run_devstone --sweep \
       --output benchmark/results/devstone_sweep.csv

Reported columns:

- ``variant``, ``depth``, ``width``, ``events``, ``dhrystones``
- ``sim_time_s`` — wall-clock simulation time in seconds
- ``transitions`` — total ``ext_trans`` + ``int_trans`` invocations
- ``ext_trans``, ``int_trans`` — split counts
- ``sink_received`` — number of events delivered to the sink
- ``events_per_s`` — transitions per second

Tuning the workload
-------------------

By default, ``int_delay`` is zero. Pass ``--dhrystones N`` to perform ``N``
units of synthetic CPU work inside each ``ext_trans``:

.. code-block:: console

   $ python -m benchmark.run_devstone --variant ho --depth 5 --width 4 \
       --events 50 --dhrystones 1000

Programmatic Use
----------------

The topology builder can also be used directly to embed DEVStone-style
workloads inside other tests:

.. code-block:: python

   from benchmark.devstone.topology import build_devstone

   ss, handles = build_devstone(
       variant="hi", depth=3, width=3, gen_count=20,
   )
   ss.simulate(50, _tm=False)

   sink = handles["sink"]
   print("delivered:", sink.get_received())

Cross-engine Comparison
-----------------------

A second runner under ``benchmark/run_compare.py`` runs the same canonical
DEVStone graph against multiple Python DEVS engines so the pyjevsim
performance baseline can be tracked. Engines covered today:

- **pyjevsim** — this package.
- **xdevs.py** 3.0+ — install with ``pip install xdevs``. Adapter wraps
  the canonical DEVStone shipped under ``xdevs.examples.devstone``.
- **PythonPDEVS** — optional adapter for a compatible checkout of the
  PythonPDEVS minimal kernel; see ``benchmark/engines/pypdevs/`` for its
  availability check.
- **reference** — a small flat-FEL DEVS engine under
  ``benchmark/engines/reference/``.

List which engines are present on the current system:

.. code-block:: console

   $ python -m benchmark.run_compare --list-engines

Run the default 9-config grid (LI/HI/HO at d=2..6) against every available
engine and persist the result:

.. code-block:: console

   $ python -m benchmark.run_compare \
       --output benchmark/results/baseline.csv

Restrict to specific engines or a single configuration:

.. code-block:: console

   $ python -m benchmark.run_compare --engines pyjevsim xdevs \
       --variant HI --depth 5 --width 4

By default each adapter injects a single seed event at t = 0 and drains the
resulting cascade. Such runs are short (well under 2 ms even at
``--depth 10 --width 10``), so timer resolution and per-call overhead weigh
heavily. ``--events N`` injects N seed events into the root input at
simulated times 0, P, 2P, ..., (N - 1)P, where ``--period P`` (default 1.0,
must be greater than 0) sets the spacing. Every cascade has zero delay, so
each finishes before the next seed arrives and the transition count is N
times the single-seed count:

.. code-block:: console

   $ python -m benchmark.run_compare --variant HI --depth 10 --width 10 \
       --repeat 3 --events 100 --period 1.0 \
       --output benchmark/results/events100.csv

The seed generator sits outside the counted atomics in every engine. With
``--events 1`` xdevs keeps its historical ``Coordinator.inject`` path, which
runs the first wave of external transitions before the timer starts and
loses work on HO. ``--xdevs-seed generator`` makes xdevs use the same
generator seeding as the other engines for single-seed runs. When N > 1 the
table and CSV gain ``events``, ``period`` and ``seed`` columns, appended
after the original ones. PythonPDEVS needs the scheduler heap-sentinel edit
documented in ``BASELINE.md`` for multi-event runs, because simulated time
advances.

``benchmark/results/BASELINE.md`` contains one historical capture and its
limitations. ``benchmark/results/COMPARE-2026-10-22.md`` records a
reproducible comparison of pyjevsim ``8135542`` and ``9a2b0d2`` with
xdevs.py, PythonPDEVS and the reference engine in both single-seed and
100-seed modes, with the environment, the exact invocations, the CSVs
(``compare-2026-10-22-single-event.csv`` and
``compare-2026-10-22-events100.csv``) and the caveats that limit how the
ratios can be read. Retain the generated CSV and environment details for
any new comparison, and compare transition counts as well as throughput.

Standard Performance Suite
--------------------------

``benchmark/suite.py`` is the suite every engine change is measured with.
It runs a fixed set of workloads against one checkout, or against a base
and a candidate checkout, and reports simulation time only (model build is
excluded) together with a parity key per run.

.. list-table::
   :header-rows: 1
   :widths: 6 50 44

   * - id
     - workload
     - parity key
   * - W1
     - DEVStone HI 10x10, 100 seeds (flattened adapter of
       ``benchmark/engines/pyjevsim``)
     - transitions, atomics, events
   * - W2
     - DEVStone LI 10x10, 1000 seeds
     - transitions, atomics, events
   * - W3
     - sparse generator -> sink, 20000 firings, period 10
       (``run_sparse`` topology)
     - fired, received, final time
   * - W4
     - 10000 passive models with an ``Infinite`` deadline plus 5 ping-pong
       pairs, 1000 events per pair
     - sent, received, final time
   * - W5
     - bank example (``examples/banksim`` of the checkout under test): 20
       generators, queue 10, 10 accountants, ``random.seed(1)``, 3000 calls
       of ``simulate(1)``, model output suppressed, ``os._exit`` guarded
     - users generated, processed, dropped, queue length
   * - W6
     - ``import pyjevsim`` (``import_s``), import plus
       ``SysExecutor(1)`` (``startup_s``) and the whole process
       (``process_s``), each in a bare ``python -E -c`` process
     - none
   * - W7
     - W1 with every executor wrapped in ``SnapshotExecutor`` through a
       ``SnapshotManager`` whose conditions never fire
     - as W1

The bank example's parity key is its model-level result, not executor
transition counts: same-instant processing follows set iteration, so
transition counts can differ between processes while the result counters
stay put on a checkout. W7 needs ``SnapshotExecutor.con_trans``, which
2.2.x does not have, and the HI chain makes most transitions confluent: in
a W7 run on 2.2.x, 32,400 of the 40,700 internal transitions (about 80%)
are confluent. On such checkouts the workload's factory adds a
``con_trans`` that mirrors the real ``int_trans``/``ext_trans`` wrappers:
the internal pre and post conditions, plus the external pre and post
conditions for each message of the bag, with a snapshot whenever one
fires. A confluent transition therefore pays the same condition cost as
the internal and external transitions it stands for, and every transition
of W7 is measured with its condition checks. The run info reports
``con_trans_shim: true`` and ``con_trans_calls`` (the number of confluent
transitions that went through the shim; ``null`` when the checkout's own
``SnapshotExecutor.con_trans`` is used). When that method lands (roadmap
CORE-5), W7 measures it instead of the shim, so a W7 comparison across
that change includes the difference between the two for about 80% of the
transitions.

Running it
~~~~~~~~~~

Compare a base and a candidate checkout (for example a ``git archive`` export
of ``main`` and a working tree), five rounds of every workload:

.. code-block:: console

   $ git archive --format=tar -o main.tar main
   $ mkdir ../base && tar -xf main.tar -C ../base
   $ python -m benchmark.suite --base ../base --cand . --rounds 5 \
       --out results.json --markdown

Restrict the workloads, change a parameter, or measure one checkout:

.. code-block:: console

   $ python -m benchmark.suite --base ../base --cand . --workloads W1,W3
   $ python -m benchmark.suite --repo . --rounds 5 --param W3.count=50000
   $ python -m benchmark.suite --list

The suite runs from the checkout that holds ``benchmark/suite.py``; each
child process loads that checkout's ``benchmark`` package and imports
``pyjevsim`` (and ``examples``, for W5) from the checkout under test, so
both sides always run identical harness code, and a child refuses to run
if ``pyjevsim`` (or ``examples``, for W5) resolves anywhere else. ``--python`` selects the
interpreter for the children.

``--pin CPUS`` restricts the suite and every child to a CPU set given as a
mask (``0xFFFF``) or a list (``0-15``, ``0,2,4``):
``SetProcessAffinityMask`` on Windows, ``os.sched_setaffinity`` on Linux.
A bare integer is a mask, as with ``taskset``: ``--pin 5`` selects CPUs 0
and 2, and ``--pin 5-5`` selects CPU 5. A CPU index at or above
``os.cpu_count()``, or above 63 on Windows (where the call covers one
processor group), is rejected with exit status 2, as is a set the platform
refuses to pin to; pinning is not available on macOS. There is no default,
because which logical CPUs are the fast cores is machine specific (on the
i7-12700 used for the 2026-10 records, the P-core threads are ``0-15``).

How a comparison is made
~~~~~~~~~~~~~~~~~~~~~~~~

* Every timed run is a fresh process. One untimed warm-up run per workload
  and side comes first (it also writes ``__pycache__``).
* Each round runs base and candidate back to back for every workload, and
  the order alternates between rounds (base first in round 1, candidate
  first in round 2, ...), so slow drift of the machine hits both sides.
* Runs are only compared when every run of both sides has the same parity
  key. Otherwise the workload is reported as ``REFUSED`` with the
  differing keys, and the exit status is 3.
* A workload whose child process fails or times out (or whose
  ``pyjevsim`` or ``examples`` resolves outside its checkout) is reported
  as ``FAILED`` and left out of the remaining rounds; the other workloads
  still run, are reported and are written by ``--out`` (with the failed
  workload's runs so far), and the exit status is 1.
* For each metric the report gives the ratio of minimums
  ``min(cand) / min(base)`` (below 1.0 means the candidate is faster), the
  median of the per-round paired ratios with their min..max spread, each
  side's own spread, and a verdict: ``noise`` when the ratio of minimums
  is within the noise floor, ``unclear`` when the median ratio disagrees
  with it, otherwise ``faster`` or ``slower``.
* ``--out`` writes every run (times, parity, round, position, interpreter,
  platform, checkout paths and git heads) as JSON; ``--markdown`` prints
  the summary as a Markdown table.

Noise policy
~~~~~~~~~~~~

These rules come from the 2026-10 performance rounds and the
performance roadmap; decide the reading rule before measuring.

* Use the ratio of minimums over interleaved fresh-process runs as the
  headline, and report the median ratio and the spread next to it.
* Do not claim a difference under 5% (``--noise-floor``) from wall-clock
  timing. Smaller effects need a quiet machine, more rounds and an A/A run
  that shows the floor is lower, or a deterministic measure such as the
  call-count budget below.
* Never compare before and after inside one process. The class-attribute
  fix of #41 reads as zero there: once one variant has used up CPython's
  per-type version tags, every later measurement in that process runs
  without attribute specialisation.
* Run an A/A comparison (the same commit exported twice) on the machine
  first. If it shows ratios beyond the floor, the floor does not hold on
  that machine at that time; add rounds or find a quiet machine.
* Put both checkouts on the same file system: import time (W6) depends on
  where the files live (a checkout under the Windows temp directory imported
  about 30% slower than one on another drive for identical code).
* Pinning cuts both ways; decide it with an A/A run on the machine. On a
  quiet hybrid CPU, pinning to the fast cores avoids a slowdown seen in
  unpinned runs longer than about 3 s (they dropped to half speed). On a
  busy machine pinning crowds the suite onto fewer cores, and in the A/A
  runs below it made the floor worse than not pinning.
* Per-workload engine shares need a sampling profiler; cProfile inflates
  the engine's share by 4.6-6.2x.

A/A noise floor measured on 2026-10-23 (``f7145e6`` exported twice to the
same directory, i7-12700, Windows 11, CPython 3.14.0, while other jobs kept
the machine 30-45% busy). Ratio of minimums, cand/base:

.. list-table::
   :header-rows: 1

   * - run
     - W1
     - W2
     - W3
     - W4
     - W5
   * - 5 rounds, pinned ``0-15``
     - 1.185
     - 0.979
     - 1.080
     - 1.027
     - 0.911
   * - 5 rounds, pinned ``0-15``
     - 1.053
     - 1.081
     - 1.102
     - 1.023
     - 0.979
   * - 5 rounds, unpinned
     - 0.992
     - 1.020
     - 1.004
     - 1.005
     - 1.004
   * - 10 rounds, unpinned
     - 1.004
     - 1.048
     - 0.976
     - 1.011
     - 0.956

On that loaded machine five rounds were not enough to hold a 5% floor
(identical code read up to 18% "slower"), per-round paired ratios ranged
from 0.75 to 1.66, and pinning to 16 logical CPUs made it worse; ten
unpinned rounds kept every ratio of minimums within 5%. Treat these as the
floor for a busy desktop, not for a quiet one.

Call-count budget
~~~~~~~~~~~~~~~~~

``tests/test_call_budget.py`` is the noise-free gate that runs in CI. It
counts Python function starts and C calls made during ``simulate()`` for a
DEVStone HI 6x8 run with 10 seeds and a small bank model, divides by the
number of transitions and fails when either exceeds the value measured on
main by more than 3%. Python-level counts are exact; C counts vary by up to
about 2.4% between runs (the schedule-queue bucket cache hit rate follows
set order), so the recorded C values are the maximum of 30 runs. The values
were recorded on Windows 11 with CPython 3.11.15, 3.12.13, 3.13.13 and
3.14.0. CI checks them with the latest 3.13 and 3.14 on Linux and the
latest 3.14 on Windows; that Linux and newer patch releases give the same
counts is expected (the engine has no platform-specific path) but was not
measured beforehand, and a version without recorded values (3.10) skips.
When an engine change adds calls on purpose, update the recorded values in
the same pull request; ``python -m tests.test_call_budget`` prints them.
``tests/test_system_object.py`` also checks that creating messages and
models and running executors never rebinds a class attribute of the hot
path classes (the regression fixed in #41).
