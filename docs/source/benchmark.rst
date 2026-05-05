DEVStone Benchmark
==================

Introduction
------------

The **DEVStone benchmark** is a synthetic workload used in the DEVS community
to characterise simulator performance independently of any application
domain. ``pyjevsim`` ships a flat implementation of the three classical
DEVStone topologies under ``benchmark/`` so that scheduler overhead can be
measured directly and tracked across releases.

Variants
--------

Every variant is built as ``Generator -> level_0 -> level_1 -> ... -> Sink``
where each *level* contains ``width`` ``DEVStoneAtomic`` instances. The
``depth`` parameter controls the number of stacked levels.

- **LI (Low Interconnect)** — one atomic per level participates in the
  forward chain. Stresses event propagation through a long but narrow graph.
- **HI (High Interconnect)** — every atomic in a level receives the level's
  input *and* feeds the next atomic in the chain. Amplifies fan-in and
  fan-out per level.
- **HO (High Output)** — same as HI plus an extra ``outx`` port on each
  atomic that goes directly to the sink, multiplying the output traffic
  observed at the top of the graph.

Layout
------

::

    benchmark/
    ├── devstone/
    │   ├── atomic.py     # DEVStoneAtomic / DEVStoneGenerator / DEVStoneSink
    │   └── topology.py   # build_devstone(variant, depth, width, ...)
    ├── run_devstone.py   # CLI runner
    └── results/          # CSV outputs from sweeps

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

By default the atomic ``int_delay`` is zero so the benchmark measures pure
simulator overhead. Pass ``--dhrystones N`` to perform ``N`` units of
synthetic CPU work inside every ``ext_trans`` and shift the measurement
toward user-code cost:

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
- **reference** — a ~150 LOC hand-rolled flat-FEL DEVS engine living under
  ``benchmark/engines/reference/`` that acts as a "no-framework-overhead"
  performance floor.

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

The captured baseline numbers and methodology notes live in
``benchmark/results/BASELINE.md``.
