Replications
============

A single pyjevsim run is sequential: models transition one at a time under
the GIL, and splitting one simulated instant across threads or processes
costs more than it saves. Independent *replications* of a stochastic model,
the same model run with different random seeds, have no such limit. Each
can run in its own process. ``pyjevsim.replication`` provides a runner for
that case.

.. code-block:: python

   # my_study.py
   import random

   from pyjevsim import (ExecutionType, SysExecutor, run_replications,
                         seed_sequence)


   def run(seed):
       random.seed(seed)                      # seed every RNG the models use
       se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
       ...                                    # register models, couple them
       se.simulate(1000, _tm=False)
       return {"served": sink.count}          # a small, picklable result


   if __name__ == "__main__":
       results = run_replications(run, seed_sequence(2026, 100), workers=8)

``run_replications(run, seeds)`` calls ``run(seed)`` once per seed on a pool
of worker processes and returns the results in the order of ``seeds``.
``examples/banksim/banksim_replications.py`` is a complete, runnable version
for the bank example.

API
---

``run_replications(run, seeds, *, workers=None, chunksize=None, mp_context="spawn", initializer=None, initargs=(), timeout=None, ordered=True, progress=None, max_tasks_per_child=None)``
   Creates a pool for this call, runs every seed and shuts the pool down.
   It starts ``min(workers, number of chunks)`` processes, so a small batch
   does not pay for idle workers.

   - ``workers``: number of processes. The default is
     ``os.process_cpu_count()`` (3.13+), otherwise ``os.cpu_count()``,
     capped at 61 on Windows. ``workers=0`` runs every replication in the
     calling process, which is useful with a debugger or profiler.
   - ``chunksize``: replications sent to a worker per task (see
     `Chunking`_).
   - ``initializer(*initargs)``: runs once in every new worker process.
   - ``timeout``: wall-clock limit for the whole batch, in seconds. When it
     expires, the workers are killed and ``ReplicationTimeoutError`` is
     raised. A ``workers=0`` run checks the limit only between
     replications.
   - ``ordered=False``: returns ``(seed, result)`` pairs in completion order
     instead of results aligned with ``seeds``.
   - ``progress(done, total)``: called in the calling process after each
     chunk completes.
   - ``max_tasks_per_child``: replaces a worker after it has run that many
     tasks (Python 3.11+; see `Worker reset`_).

``ReplicationPool(workers=None, *, mp_context="spawn", initializer=None, initargs=(), max_tasks_per_child=None)``
   A context manager that keeps one pool alive for several batches.
   Starting a pool takes a noticeable share of a short batch (see
   `Start-up cost and break-even`_), so reuse a pool for a study that runs
   several batches:

   .. code-block:: python

      with ReplicationPool(workers=8) as pool:
          base = pool.map(run_base, seeds)
          variant = pool.map(run_variant, seeds)

   ``pool.map(run, seeds, *, chunksize=None, timeout=None, ordered=True,
   progress=None)`` takes the same per-batch arguments as
   ``run_replications``. Worker processes start on demand with the first
   ``map``. If a batch breaks the pool or times out, the pool discards its
   workers and starts new ones on the next ``map``.

``seed_sequence(base_seed, n)``
   Returns ``n`` distinct seeds below 2**63, derived from ``base_seed`` with
   BLAKE2b. The derivation uses only ``hashlib``, so it gives the same seeds
   on every platform and Python version. It does not touch the global
   ``random`` state. It is prefix-stable: ``seed_sequence(b, 200)[:100] ==
   seed_sequence(b, 100)``, so adding replications to a study leaves the
   seeds of the earlier ones unchanged.

The spawn and import rules
--------------------------

The default start method is ``spawn`` on every platform. It is the only
method on Windows and the default on macOS. A spawned worker is a new
interpreter that receives ``run`` *by reference*: the module name and the
function name are pickled, and the worker imports that module. This leads to
three rules:

1. ``run`` must be defined at module top level. A lambda, a nested function
   or a closure cannot be pickled. Bind parameters with
   ``functools.partial(run, ticks=3000)`` instead. The runner pickles ``run``
   before it starts any worker and raises ``TypeError`` with this advice if
   pickling fails.
2. If ``run`` is defined in the script you execute, the script body must be
   guarded with ``if __name__ == "__main__":``. The worker imports the script
   as ``__mp_main__``; without the guard it would start the experiment
   again. Multiprocessing refuses that, and the runner reports it as
   ``BrokenReplicationPool``.
3. ``run`` cannot live in an interactive ``__main__`` (a REPL, a notebook
   or ``python -c``), because a worker cannot import it. The runner detects
   this case and raises ``TypeError``. Put ``run`` in a module and import
   it.

The result of ``run`` must also be picklable. The worker pickles it, so a
result that cannot be pickled is reported as a failure of that seed only.
Keep results small (counters, summary statistics, a few arrays). Returning
the whole ``SysExecutor`` pickles the full model graph.

A ``run`` that itself calls ``run_replications`` or ``ReplicationPool.map``
runs the inner batch sequentially inside its worker instead of starting a
nested pool. ``pyjevsim.replication.in_replication_worker()`` tells ``run``
whether it is running in a worker.

What is and is not reproducible
-------------------------------

The runner guarantees two things: each replication receives its own seed,
and results come back aligned with ``seeds`` regardless of completion order.

It does **not** guarantee that re-running a seed reproduces the run bit for
bit, whether in another process, in another worker or with
``workers=0``. Two engine properties prevent that today:

- Models that transition in the same simulated instant are processed in set
  iteration order, and that order depends on object identity, which can
  change between processes.
- The engine does not own a random number generator. Models draw from
  whatever ``run`` seeded, often the shared global ``random`` stream, so the
  order of draws follows the order of transitions.

Engine-owned seeds and a deterministic same-instant order are later roadmap
items. Until then, treat a seed as giving an *independent* replication, not
a *repeatable* one. In the bank example, the final counters happened to
match for all 20 seeds between the in-process and the pooled run on the
machine below, but that is an observation, not a guarantee.

Errors
------

The runner uses one error policy. Every replication runs to completion
first. If any ``run(seed)`` raised (including ``SystemExit``), the runner
then raises ``ReplicationError``, which carries:

- ``failures``: one ``ReplicationFailure`` per failing seed, in seed order,
  with ``seed``, ``exc_type``, ``message``, the worker ``traceback`` text and,
  if it could be pickled, the ``exception`` itself.
- ``failed_seeds`` and ``first_traceback``. The error message names the
  failing seeds and includes the first traceback.
- ``results``: one entry per seed, holding the result of each successful
  replication and ``None`` for each failed one.

There is no skip mode. If partial results are acceptable, catch
``ReplicationError`` and use ``.results`` and ``.failures``. A failing
seed leaves the pool usable.

Two cases cannot be attributed to a single seed:

``BrokenReplicationPool``
   A worker process died. Common causes are ``os._exit`` inside a model
   (the bank example's ``BankResult`` calls ``os._exit(0)`` when it reaches
   ``max_user``), a crash in an extension module, the machine running out
   of memory, an initializer that raised, or a missing ``__main__`` guard.
   ``unfinished`` lists the seeds that never returned, and the seed that
   killed the worker is among them. Run those seeds with ``workers=0`` to
   see the failure in-process.

``ReplicationTimeoutError`` (also a ``TimeoutError``)
   ``timeout`` expired. The workers were killed, and ``unfinished`` lists the
   seeds that had not returned.

In both cases, ``results`` keeps everything that did finish.

Worker reset
------------

Workers are reused for many replications, so process-global state persists
from one replication to the next in the same worker. Examples:

- Module-level caches, class-level counters and registries.
- The global ``random`` stream if a model draws from it without ``run``
  reseeding it.
- ``SysExecutor.simulate()`` with the default ``_tm=True`` installs
  pyjevsim's SIGINT/SIGTERM handler in the worker. A Ctrl+C then ends each
  running replication early, and ``run`` returns its partial result as if
  it had finished, instead of stopping the batch. Pass ``_tm=False`` inside
  ``run``; a replication does not need that handler.

``max_tasks_per_child=k`` (Python 3.11+) replaces a worker with a fresh
process after ``k`` tasks. A task is one chunk, so ``chunksize=1,
max_tasks_per_child=1`` gives every replication a fresh interpreter at the
cost of one process start per replication. Worker reset contains state that
leaks between replications. It does not prevent a worker from dying:
``os._exit`` still kills the worker and raises ``BrokenReplicationPool``.

Chunking
--------

Each task carries ``chunksize`` replications to a worker. The default is
``max(1, len(seeds) // (4 * workers))``. That gives about four chunks per
worker, which keeps workers balanced when replication times vary while
spreading the per-task round trip over several replications when each one
is short. Examples: 20 seeds on 4 workers gives 1, 200 seeds on 8 workers
gives 6, and 2000 seeds on 8 workers gives 62. The runner keeps at most two
chunks per worker in flight and submits the rest as chunks finish.

On the machine below, one task costs about 150 microseconds of round trip
on a warm 8-worker pool. Chunking therefore matters only when a replication
takes about a millisecond or less:

- A replication that does nothing costs 148 µs per seed with
  ``chunksize=1``, 9.6 µs with 16 and 2.7 µs with 63.
- A bank replication of about 1.1 ms (30 ticks, 2000 seeds) took 0.39 s with
  ``chunksize=1`` and 0.36 s with 16. The default of 62 took 0.37 s.
- At about 9 ms per replication (200 seeds), ``chunksize`` 1, the default
  and 25 were within run-to-run noise. Pool start-up and machine load
  dominated.

The window of in-flight chunks matters more than the chunk size.
Submitting all 2000 chunks at once made ``chunksize=1`` cost 578 µs per
no-op seed instead of 148 µs, and 1.36 s instead of 0.39 s for the 1.1 ms
bank batch.

Start-up cost and break-even
----------------------------

A spawned worker is a new interpreter that imports pyjevsim and the module
of ``run`` before it does any work. The performance roadmap estimates the
cost on Windows at 0.75-1.0 s to start a pool plus 0.2-0.3 s of imports per
process. From that it *estimates* that a pool pays off once the batch holds
roughly 1.25 s of sequential work.

On the machine below, starting a pool and running one trivial task per
worker measured 0.19 s for 1 worker, 0.26 s for 4, 0.52 s for 8, 0.66 s for
12 and 0.60 s for 20 (median of 5). With ``T`` the total sequential time,
``w`` the number of workers and ``S`` the start-up cost, the batch takes
roughly ``S + T / w`` plus contention. The pool breaks even near
``T = S * w / (w - 1)``, about 0.35-0.7 s here. Treat about 1 s of total
sequential work as the point below which ``workers=0`` (or a smaller
pool) is the safer choice. Reuse a ``ReplicationPool`` when a study runs
several batches.

Measured throughput
-------------------

.. note::

   Measured on a **shared** machine with other jobs running: Intel Core
   i7-12700 (8 performance and 4 efficiency cores, 20 hardware threads),
   Windows 11 10.0.26300, CPython 3.14.0, pyjevsim 2.2.0 main (148c81b)
   plus this runner. Machine-wide CPU use during the sequential runs was
   27-40% (median about 33%); this process accounted for about 5 points of
   that. Figures are medians of 5 interleaved rounds (3 for the 30000-tick
   case). Speed-ups are ratios of medians and include pool start-up unless
   marked "warm". Expect different numbers on an idle machine, and smaller
   speed-ups at high worker counts on a busier one.

Bank example (``examples/banksim/banksim_replications.py``: 20 generators,
10 accountants, ``simulate(1, _tm=False)`` per tick), 20 seeds:

============================  ===================  ===================
Configuration                 3000 ticks           30000 ticks
                              (~0.09 s per seed)   (~1.0 s per seed)
============================  ===================  ===================
sequential, in-process        1.89 s               20.3 s
``workers=4``                 0.79 s (2.4x)        6.2 s (3.3x)
``workers=8``                 0.68 s (2.8x)        4.8 s (4.3x)
``workers=12``                0.68 s (2.8x)        4.4 s (4.7x)
``workers=20`` (cpu_count)    0.83 s (2.3x)        4.2 s (4.8x)
warm pool, 12 workers         0.34 s (5.5x)        4.2 s (4.8x)
warm pool, 20 workers         0.33 s (5.7x)        3.6 s (5.6x)
============================  ===================  ===================

For the short batch, pool start-up (0.5-0.66 s for 8-20 workers, measured
separately) is comparable to the whole batch, so 8-12 workers do as well as
20 and a warm pool roughly doubles the speed-up. For the long batch, 20 seeds on 12-20 workers leave little work
to balance, and per-replication time rises from 1.0 s alone to about 3.5 s
with 20 concurrent replications on a partly loaded hybrid CPU. The
roadmap's 3.3-7.6x replication throughput was measured separately on a
shared 12-core/20-thread machine; this table does not reproduce that
setup.

Short replications: 200 seeds of a ~9 ms bank run (300 ticks), sequential
1.87 s. With 8 workers the batch took 0.70 s with ``chunksize=1``, 0.74 s
with the default (6) and 0.71 s with 25 (2.5-2.6x). With 20 workers it took
0.98-1.03 s whatever the chunk size (1.8-1.9x).

.. warning::

   **Windows power throttling distorts sequential baselines.** Windows 11
   can apply EcoQoS throttling to a CPU-bound process started from a
   background console. During these measurements, an in-process loop of
   bank replications slowed from 0.09 s to 0.25-0.5 s per replication
   after about 3 s of running, while freshly spawned workers ran at full
   speed. With throttling left on, the 20-seed sequential baseline measured
   1.8-6.6 s and the "speed-ups" reached 6-8x. The numbers above come from
   a harness that opted both the parent and the workers out of throttling
   (``SetProcessInformation(ProcessPowerThrottling)``, applied in the
   harness through ``initializer``, not by pyjevsim). Long-running workers
   can be throttled in the same way.

Relation to design of experiments
---------------------------------

A design of experiments is a loop of replication batches, one per design
point. Bind each point's parameters with ``functools.partial`` and reuse one
pool:

.. code-block:: python

   seeds = seed_sequence(7, 30)
   with ReplicationPool(workers=8) as pool:
       table = {point: pool.map(functools.partial(run, **point), seeds)
                for point in design}

Reusing the same seeds at every design point (common random numbers)
reduces variance only to the extent that a seed reproduces a run, which is
not guaranteed yet (see above). The roadmap's ``DoEManager`` port (SC-7)
will build on this runner rather than on a separate pool.

Reference
---------

.. automodule:: pyjevsim.replication
   :members: run_replications, ReplicationPool, seed_sequence,
             ReplicationError, ReplicationFailure, BrokenReplicationPool,
             ReplicationTimeoutError, default_chunksize, default_workers,
             in_replication_worker
   :show-inheritance:
