"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Replication runner: run one independent simulation per seed on a pool of
worker processes and collect the results in seed order.

A single pyjevsim run is sequential (the GIL and the per-instant barrier make
intra-run parallelism a net loss), but independent replications of a
stochastic model parallelise well across processes.  The user supplies a
picklable callable ``run(seed) -> result``; it builds a ``SysExecutor``, seeds
its random number generators from ``seed``, simulates and returns whatever it
needs (counters, statistics, a small dict).  :func:`run_replications` calls it
once per seed on a persistent process pool and returns the results in the
order of ``seeds``.

What is guaranteed: every replication receives its own seed, and results
come back aligned with ``seeds``.  What is *not* guaranteed yet: that a given
seed reproduces a run bit for bit in another process.  Same-instant
processing currently follows set iteration order, and engine-owned seeds are
a later roadmap item; see ``docs/source/replication.rst``.

Only ``os`` and ``sys`` are imported at module level.  ``multiprocessing``,
``concurrent.futures``, ``pickle``, ``traceback`` and ``hashlib`` are loaded
on first use so that ``import pyjevsim`` stays light.
"""

import os
import sys

__all__ = [
    "BrokenReplicationPool",
    "ReplicationError",
    "ReplicationFailure",
    "ReplicationPool",
    "ReplicationTimeoutError",
    "default_chunksize",
    "default_workers",
    "in_replication_worker",
    "run_replications",
    "seed_sequence",
]

# ProcessPoolExecutor refuses more than 61 workers on Windows
# (WaitForMultipleObjects limit).
_MAX_WINDOWS_WORKERS = 61

# Set by the worker initializer; a run_replications() call made inside a
# replication then runs sequentially instead of starting a nested pool.
_IN_WORKER = False

_MISSING = object()

# Chunks kept in flight per worker; the rest are submitted as chunks finish.
_WINDOW_PER_WORKER = 2


def in_replication_worker():
    """Return True when called inside a worker process of a replication pool."""
    return _IN_WORKER


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

class ReplicationFailure:
    """One replication that raised instead of returning a result.

    Attributes:
        index (int): Position of the seed in the ``seeds`` sequence.
        seed: The seed passed to ``run``.
        exc_type (str): Qualified name of the exception class.
        message (str): ``str()`` of the exception.
        traceback (str): Formatted traceback from the worker process.
        exception (BaseException or None): The exception itself when it could
            be pickled back from the worker, otherwise None.
    """

    __slots__ = ("index", "seed", "exc_type", "message", "traceback",
                 "exception")

    def __init__(self, index, seed, exc_type, message, traceback,
                 exception=None):
        self.index = index
        self.seed = seed
        self.exc_type = exc_type
        self.message = message
        self.traceback = traceback
        self.exception = exception

    def __reduce__(self):
        return (ReplicationFailure,
                (self.index, self.seed, self.exc_type, self.message,
                 self.traceback, self.exception))

    def __repr__(self):
        return (f"ReplicationFailure(index={self.index}, seed={self.seed!r}, "
                f"{self.exc_type}: {self.message})")


class ReplicationError(RuntimeError):
    """Raised after a batch in which at least one replication did not finish.

    The runner always collects every replication before raising, so the
    results of the replications that did succeed are not lost.

    Attributes:
        failures (list[ReplicationFailure]): Replications whose ``run`` raised,
            in seed order.
        unfinished (list): Seeds that never completed because the pool broke
            or the batch timed out (empty for plain failures).
        results (list): One entry per seed, aligned with ``seeds``; the result
            of each successful replication and None for every failed or
            unfinished one.
    """

    def __init__(self, message, failures=(), unfinished=(), results=None):
        super().__init__(message)
        self.failures = list(failures)
        self.unfinished = list(unfinished)
        self.results = results

    @property
    def failed_seeds(self):
        """Seeds whose replication raised, in seed order."""
        return [f.seed for f in self.failures]

    @property
    def first_traceback(self):
        """Worker traceback of the first failing seed, or None."""
        return self.failures[0].traceback if self.failures else None


class BrokenReplicationPool(ReplicationError):
    """A worker process died (``os._exit``, a crash, an out-of-memory kill,
    a failing initializer or an unguarded ``__main__`` under spawn).

    ``unfinished`` lists the seeds that never returned; the replication that
    killed the worker is among them.
    """


class ReplicationTimeoutError(ReplicationError, TimeoutError):
    """The batch did not finish within ``timeout`` seconds.

    The pool's worker processes are terminated; ``unfinished`` lists the
    seeds that had not returned.
    """


# --------------------------------------------------------------------------
# Defaults and seeds
# --------------------------------------------------------------------------

def default_workers():
    """Number of worker processes used when ``workers`` is None.

    ``os.process_cpu_count()`` (Python 3.13+, honours CPU affinity) or else
    ``os.cpu_count()``, capped at 61 on Windows.
    """
    count_fn = getattr(os, "process_cpu_count", None) or os.cpu_count
    n = count_fn() or 1
    if sys.platform == "win32":
        n = min(n, _MAX_WINDOWS_WORKERS)
    return n


def default_chunksize(n_seeds, workers):
    """Replications sent to a worker per task when ``chunksize`` is None.

    ``max(1, n_seeds // (4 * workers))``: about four chunks per worker, which
    keeps workers load-balanced when replication times vary while amortising
    the per-task inter-process round trip over several replications when
    each one is short.  With 20 seeds and 4 workers this is 1; with 200 seeds
    and 12 workers it is 4.
    """
    workers = max(1, int(workers))
    return max(1, int(n_seeds) // (4 * workers))


def seed_sequence(base_seed, n):
    """Return ``n`` distinct 63-bit seeds derived from ``base_seed``.

    Seed ``i`` is the first 64 bits of BLAKE2b over
    ``b"pyjevsim.seed_sequence:<base_seed>:<i>"`` shifted right by one, so it
    fits a signed 64-bit integer (Java ``long``, NumPy).  The derivation uses
    only ``hashlib``: it is the same on every platform and Python version,
    it does not touch the global ``random`` state, and it is prefix-stable
    (``seed_sequence(b, 10)[:5] == seed_sequence(b, 5)``), so a study can be
    extended with more replications without changing the earlier seeds.
    Neighbouring base seeds give unrelated sequences.  A duplicate value
    (probability about n**2 / 2**64) is skipped, so all seeds are distinct.

    Args:
        base_seed (int): The experiment's master seed.
        n (int): Number of seeds to derive.

    Returns:
        list[int]: ``n`` distinct non-negative integers below 2**63.
    """
    import hashlib
    import operator

    base_seed = operator.index(base_seed)
    n = operator.index(n)
    if n < 0:
        raise ValueError("n must be >= 0")
    seeds = []
    seen = set()
    i = 0
    while len(seeds) < n:
        digest = hashlib.blake2b(
            b"pyjevsim.seed_sequence:%d:%d" % (base_seed, i),
            digest_size=8).digest()
        i += 1
        value = int.from_bytes(digest, "big") >> 1
        if value in seen:
            continue
        seen.add(value)
        seeds.append(value)
    return seeds


# --------------------------------------------------------------------------
# Worker side
# --------------------------------------------------------------------------

def _worker_init(initializer, initargs):
    global _IN_WORKER
    _IN_WORKER = True
    if initializer is not None:
        initializer(*initargs)


def _describe(exc):
    import pickle
    import traceback

    text = "".join(traceback.format_exception(type(exc), exc,
                                              exc.__traceback__))
    try:
        exc_copy = pickle.loads(pickle.dumps(exc))
    except Exception:
        exc_copy = None
    return (type(exc).__qualname__, str(exc), text, exc_copy)


def _call(run, seed, serialize):
    """Run one replication; return (ok, payload).

    With ``serialize`` the result is pickled here, inside the worker, so an
    unpicklable result is reported against its own seed instead of failing
    the whole chunk.
    """
    try:
        result = run(seed)
    except (Exception, SystemExit) as exc:
        return False, _describe(exc)
    if not serialize:
        return True, result
    import pickle
    try:
        return True, pickle.dumps(result, pickle.HIGHEST_PROTOCOL)
    except Exception as exc:
        info = _describe(exc)
        return False, (info[0],
                       f"the result of run({seed!r}) is not picklable: "
                       f"{info[1]}", info[2], info[3])


def _run_chunk(run, items):
    """Task executed in a worker: run every (index, seed) of one chunk."""
    return [(index,) + _call(run, seed, True) for index, seed in items]


# --------------------------------------------------------------------------
# Parent side
# --------------------------------------------------------------------------

def _check_picklable(obj, what, start_method):
    import pickle

    try:
        data = pickle.dumps(obj)
    except Exception as exc:
        raise TypeError(
            f"{what} must be picklable to be sent to worker processes: "
            f"{exc}. Define it at module top level (not a lambda, a nested "
            f"function or a bound method of an unpicklable object), or bind "
            f"arguments with functools.partial on a top-level function."
        ) from exc
    if start_method == "fork":
        return
    main = sys.modules.get("__main__")
    if getattr(main, "__file__", None) is None and (
            b"\x8c\x08__main__" in data or b"c__main__\n" in data):
        raise TypeError(
            f"{what} refers to __main__, but __main__ is an interactive "
            f"session (REPL, notebook or python -c) that a {start_method!r} "
            f"worker cannot import. Move it into an importable module and "
            f"import it from there.")


def _resolve_context(mp_context):
    import multiprocessing

    if mp_context is None or isinstance(mp_context, str):
        return multiprocessing.get_context(mp_context)
    return mp_context


def _format_seeds(seeds, limit=8):
    if len(seeds) <= limit:
        return ", ".join(repr(s) for s in seeds)
    head = ", ".join(repr(s) for s in seeds[:limit])
    return f"{head}, ... ({len(seeds)} seeds)"


class _Collector:
    """Accumulates results and failures of one batch."""

    def __init__(self, seeds, ordered, progress):
        self.seeds = seeds
        self.ordered = ordered
        self.progress = progress
        self.results = [_MISSING] * len(seeds)
        self.completion = []
        self.failures = []
        self.done = 0

    def add(self, index, ok, payload, loads=None):
        if ok:
            value = loads(payload) if loads is not None else payload
            self.results[index] = value
            if not self.ordered:
                self.completion.append((self.seeds[index], value))
        else:
            self.failures.append(
                ReplicationFailure(index, self.seeds[index], *payload))

    def advance(self, count):
        self.done += count
        if self.progress is not None:
            self.progress(self.done, len(self.seeds))

    def partial(self):
        return [None if r is _MISSING else r for r in self.results]

    def unfinished(self):
        done = set(f.index for f in self.failures)
        return [s for i, (s, r) in enumerate(zip(self.seeds, self.results))
                if r is _MISSING and i not in done]

    def finish(self):
        if self.failures:
            self.failures.sort(key=lambda f: f.index)
            first = self.failures[0]
            raise ReplicationError(
                f"{len(self.failures)} of {len(self.seeds)} replications "
                f"failed (seeds: {_format_seeds(self.failed_seeds())}); "
                f"first failure, seed {first.seed!r}:\n{first.traceback}",
                self.failures, (), self.partial())
        if self.ordered:
            return self.results
        return self.completion

    def failed_seeds(self):
        return [f.seed for f in self.failures]


def _run_sequential(run, seeds, initializer, initargs, timeout, ordered,
                    progress):
    import time

    if initializer is not None:
        initializer(*initargs)
    collector = _Collector(seeds, ordered, progress)
    deadline = None if timeout is None else time.monotonic() + timeout
    for index, seed in enumerate(seeds):
        if deadline is not None and time.monotonic() >= deadline:
            unfinished = seeds[index:]
            raise ReplicationTimeoutError(
                f"replication batch exceeded timeout={timeout} s; "
                f"{len(unfinished)} seeds not run: "
                f"{_format_seeds(unfinished)}",
                collector.failures, unfinished, collector.partial())
        ok, payload = _call(run, seed, False)
        collector.add(index, ok, payload)
        collector.advance(1)
    return collector.finish()


class ReplicationPool:
    """A persistent pool of worker processes for several replication batches.

    Starting a ``spawn`` pool is not free (measured on one Windows machine:
    about 0.2 s for one worker and about 0.6 s for 12-20, see the
    replication guide for the figures), so a study that runs several
    batches (several scenarios, a design of experiments) should pay it once::

        with ReplicationPool(workers=8) as pool:
            baseline = pool.map(run_baseline, seed_sequence(1, 100))
            variant = pool.map(run_variant, seed_sequence(1, 100))

    Worker processes are started on demand by the first ``map`` and reused
    until the pool is closed.  If a batch breaks the pool (a worker died) or
    times out, the workers are discarded and a fresh set is started by the
    next ``map``.

    Args:
        workers (int or None): Worker processes; None means
            :func:`default_workers`.  0 runs every replication in the calling
            process (no pool; useful for debugging and profiling).
        mp_context (str, multiprocessing context or None): Start method.
            The default ``"spawn"`` behaves the same on Windows, macOS and
            Linux; None uses the platform default.
        initializer (callable or None): Called once in every new worker
            process with ``*initargs`` (in sequential mode, once in the
            calling process).  Must be picklable.
        initargs (tuple): Arguments for ``initializer``.
        max_tasks_per_child (int or None): Replace a worker process after it
            has completed this many tasks (Python 3.11+).  A task is one
            chunk, so ``chunksize=1, max_tasks_per_child=1`` gives every
            replication a fresh interpreter.  Use it when ``run`` leaks
            process-global state between replications (module-level caches,
            the global ``random`` stream if a model draws from it without
            reseeding, class-level counters, memory growth).  Each
            replacement costs a process start-up.
    """

    def __init__(self, workers=None, *, mp_context="spawn", initializer=None,
                 initargs=(), max_tasks_per_child=None):
        if workers is None:
            workers = default_workers()
        workers = int(workers)
        if workers < 0:
            raise ValueError("workers must be >= 0")
        if initializer is not None and not callable(initializer):
            raise TypeError("initializer must be callable")
        if max_tasks_per_child is not None:
            if sys.version_info < (3, 11):
                raise ValueError(
                    "max_tasks_per_child requires Python 3.11 or later "
                    "(concurrent.futures.ProcessPoolExecutor gained it in "
                    "3.11)")
            if int(max_tasks_per_child) < 1:
                raise ValueError("max_tasks_per_child must be >= 1")
        self._workers = workers
        self._mp_context = mp_context
        self._initializer = initializer
        self._initargs = tuple(initargs)
        self._max_tasks_per_child = max_tasks_per_child
        self._executor = None
        self._closed = False

    @property
    def workers(self):
        """Number of worker processes (0 means in-process execution)."""
        return self._workers

    # -- context manager ----------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.close()
        else:
            self.terminate()
        return False

    def close(self):
        """Shut the pool down after outstanding work; idempotent."""
        self._closed = True
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=True)

    def terminate(self):
        """Kill the worker processes now and cancel queued work; idempotent."""
        self._closed = True
        self._discard_executor()

    # -- internals ----------------------------------------------------------

    def _sequential(self):
        return self._workers == 0 or _IN_WORKER

    def _start_method(self):
        return _resolve_context(self._mp_context).get_start_method()

    def _get_executor(self):
        if self._executor is None:
            from concurrent.futures import ProcessPoolExecutor

            kwargs = {}
            if self._max_tasks_per_child is not None:
                kwargs["max_tasks_per_child"] = int(self._max_tasks_per_child)
            self._executor = ProcessPoolExecutor(
                max_workers=self._workers,
                mp_context=_resolve_context(self._mp_context),
                initializer=_worker_init,
                initargs=(self._initializer, self._initargs),
                **kwargs)
        return self._executor

    def _discard_executor(self):
        executor, self._executor = self._executor, None
        if executor is None:
            return
        kill = getattr(executor, "kill_workers", None)  # Python 3.14+
        if kill is not None:
            try:
                kill()
            except Exception:
                pass
        else:
            for proc in list((getattr(executor, "_processes", None)
                              or {}).values()):
                try:
                    proc.kill()
                except Exception:
                    pass
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    # -- public -------------------------------------------------------------

    def map(self, run, seeds, *, chunksize=None, timeout=None, ordered=True,
            progress=None):
        """Run ``run(seed)`` for every seed on the pool.

        Args:
            run (callable): Picklable ``run(seed) -> result``; the result must
                be picklable too.  Under ``spawn`` the worker re-imports the
                module that defines ``run``, so define it at module top level.
            seeds (iterable): Seeds, one replication each.
            chunksize (int or None): Replications per task; None means
                :func:`default_chunksize`.
            timeout (float or None): Wall-clock limit for the whole batch in
                seconds.  When it expires the workers are killed and
                :class:`ReplicationTimeoutError` is raised.  In sequential
                mode it is checked between replications only.
            ordered (bool): True returns ``[result, ...]`` aligned with
                ``seeds``.  False returns ``[(seed, result), ...]`` in
                completion order.
            progress (callable or None): ``progress(done, total)`` called in
                the calling process after each completed chunk.

        Returns:
            list: See ``ordered``.

        Raises:
            ReplicationError: One or more replications raised; raised after
                all the others finished.  ``failures`` names every failing
                seed and ``results`` keeps the successful results.
            BrokenReplicationPool: A worker process died.
            ReplicationTimeoutError: ``timeout`` expired.
            TypeError: ``run`` or ``initializer`` cannot be sent to a worker.
        """
        if self._closed:
            raise ValueError("ReplicationPool is closed")
        seeds = list(seeds)
        if not seeds:
            return []
        if self._sequential():
            return _run_sequential(run, seeds, self._initializer,
                                   self._initargs, timeout, ordered, progress)
        if chunksize is None:
            chunksize = default_chunksize(len(seeds), self._workers)
        chunksize = int(chunksize)
        if chunksize < 1:
            raise ValueError("chunksize must be >= 1")

        start_method = self._start_method()
        _check_picklable(run, "run", start_method)
        if self._initializer is not None and self._executor is None:
            _check_picklable(self._initializer, "initializer", start_method)

        try:
            return self._dispatch(run, seeds, chunksize, timeout, ordered,
                                  progress)
        except ReplicationError as exc:
            # Failures inside run() leave the workers healthy; a broken pool
            # or a timeout does not.
            if isinstance(exc, (BrokenReplicationPool,
                                ReplicationTimeoutError)):
                self._discard_executor()
            raise
        except BaseException:
            # Interrupted (Ctrl-C, a progress callback raised): do not leave
            # workers running stale tasks.
            self._discard_executor()
            raise

    def _dispatch(self, run, seeds, chunksize, timeout, ordered, progress):
        import pickle
        import time
        from concurrent.futures import FIRST_COMPLETED, wait
        from concurrent.futures.process import BrokenProcessPool

        executor = self._get_executor()
        collector = _Collector(seeds, ordered, progress)
        indexed = list(enumerate(seeds))
        chunks = iter([indexed[start:start + chunksize]
                       for start in range(0, len(indexed), chunksize)])
        futures = {}
        pending = set()
        broken = None

        def submit_next():
            # Keep at most _WINDOW_PER_WORKER chunks per worker in flight:
            # wait() re-arms a waiter on every pending future, so submitting
            # thousands of chunks up front makes collection quadratic
            # (measured 570 us per no-op task with 2000 submitted at once
            # versus 140 us with a window of 16 on 8 workers).
            nonlocal broken
            chunk = next(chunks, None)
            if chunk is None or broken is not None:
                return
            try:
                fut = executor.submit(_run_chunk, run, chunk)
            except BrokenProcessPool as exc:
                broken = exc
                return
            futures[fut] = chunk
            pending.add(fut)

        for _ in range(_WINDOW_PER_WORKER * self._workers):
            submit_next()

        deadline = None if timeout is None else time.monotonic() + timeout
        while pending:
            remaining = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    unfinished = collector.unfinished()
                    raise ReplicationTimeoutError(
                        f"replication batch exceeded timeout={timeout} s; "
                        f"worker processes were terminated; "
                        f"{len(unfinished)} seeds unfinished: "
                        f"{_format_seeds(unfinished)}",
                        sorted(collector.failures, key=lambda f: f.index),
                        unfinished, collector.partial())
            done, _ = wait(pending, timeout=remaining,
                           return_when=FIRST_COMPLETED)
            pending.difference_update(done)
            for fut in done:
                chunk = futures.pop(fut)
                submit_next()
                try:
                    out = fut.result()
                except BrokenProcessPool as exc:
                    broken = exc
                    continue
                except Exception as exc:
                    # The task itself failed outside run(): typically the
                    # arguments could not be pickled by the executor.
                    info = _describe(exc)
                    for index, _seed in chunk:
                        collector.add(index, False, info)
                    collector.advance(len(chunk))
                    continue
                for index, ok, payload in out:
                    collector.add(index, ok, payload, pickle.loads)
                collector.advance(len(chunk))

        if broken is not None:
            unfinished = collector.unfinished()
            raise BrokenReplicationPool(
                f"a worker process terminated abruptly while running the "
                f"replication batch; {len(unfinished)} of {len(seeds)} seeds "
                f"did not return ({_format_seeds(unfinished)}) and the one "
                f"that killed the worker is among them. Typical causes: "
                f"os._exit() or a crash inside a model, the machine running "
                f"out of memory, an initializer that raised, or a script "
                f"without an 'if __name__ == \"__main__\":' guard under "
                f"spawn. Re-run those seeds with workers=0 to see the error "
                f"in-process.",
                sorted(collector.failures, key=lambda f: f.index),
                unfinished, collector.partial()) from broken
        return collector.finish()


def run_replications(run, seeds, *, workers=None, chunksize=None,
                     mp_context="spawn", initializer=None, initargs=(),
                     timeout=None, ordered=True, progress=None,
                     max_tasks_per_child=None):
    """Run ``run(seed)`` once per seed on a process pool.

    A pool is created for this call, reused for every seed and shut down
    before returning; to share one pool across several batches use
    :class:`ReplicationPool`.  The number of processes started is
    ``min(workers, number of chunks)``, so a small batch does not pay for
    idle workers.

    Called from inside a replication worker (a ``run`` that itself calls
    ``run_replications``), the inner batch runs sequentially in that worker
    instead of starting a nested pool.

    Error policy: every replication is run to completion first.  If any of
    them raised, :class:`ReplicationError` is raised afterwards; it names
    every failing seed, carries the first worker traceback in its message
    and keeps the successful results in ``.results`` (None for failed
    seeds).  There is no skip mode: catch the error and use ``.results`` and
    ``.failures`` when partial results are acceptable.

    Args:
        run (callable): Picklable ``run(seed) -> picklable result``.
        seeds (iterable): One replication per seed; see :func:`seed_sequence`.
        workers (int or None): Worker processes, default
            :func:`default_workers`; 0 runs in the calling process.
        chunksize (int or None): Replications per task, default
            :func:`default_chunksize`.
        mp_context (str, context or None): Start method, default "spawn".
        initializer (callable or None): Called once per worker process.
        initargs (tuple): Arguments for ``initializer``.
        timeout (float or None): Wall-clock limit for the whole batch.
        ordered (bool): True (default) returns results aligned with
            ``seeds``; False returns ``(seed, result)`` pairs in completion
            order.
        progress (callable or None): ``progress(done, total)`` after each
            completed chunk.
        max_tasks_per_child (int or None): Recycle workers after this many
            tasks (Python 3.11+); see :class:`ReplicationPool`.

    Returns:
        list: Results in seed order (or pairs, see ``ordered``).
    """
    seeds = list(seeds)
    if not seeds:
        return []
    if workers is None:
        workers = default_workers()
    workers = int(workers)
    if workers > 0 and not _IN_WORKER:
        if chunksize is None:
            chunksize = default_chunksize(len(seeds), workers)
        n_chunks = -(-len(seeds) // max(1, int(chunksize)))
        workers = min(workers, n_chunks)
    with ReplicationPool(workers, mp_context=mp_context,
                         initializer=initializer, initargs=initargs,
                         max_tasks_per_child=max_tasks_per_child) as pool:
        return pool.map(run, seeds, chunksize=chunksize, timeout=timeout,
                        ordered=ordered, progress=progress)
