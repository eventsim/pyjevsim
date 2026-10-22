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
