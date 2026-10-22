"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Tests for the replication runner (pyjevsim.replication).

Each test that starts a pool pays a spawn start-up (about 0.3-1 s on
Windows), so pools use two workers and the module stays well under 20 s.
"""
import os
import random
import sys

import pytest

import pyjevsim
from pyjevsim.replication import (
    BrokenReplicationPool,
    ReplicationError,
    ReplicationPool,
    ReplicationTimeoutError,
    default_chunksize,
    in_replication_worker,
    run_replications,
    seed_sequence,
)

from . import replication_funcs as rf


def _expected(seed):
    return {"seed": seed, "draw": random.Random(seed).random()}


def test_package_exports():
    for name in ("run_replications", "ReplicationPool", "ReplicationError",
                 "seed_sequence"):
        assert hasattr(pyjevsim, name)


def test_results_in_seed_order_with_two_workers():
    seeds = list(range(8))
    calls = []
    results = run_replications(rf.echo_slow, seeds, workers=2, chunksize=1,
                               progress=lambda d, t: calls.append((d, t)))
    assert results == [_expected(s) for s in seeds]
    assert [d for d, _ in calls] == list(range(1, 9))
    assert all(t == 8 for _, t in calls)


def test_failing_seed_raises_naming_it_after_collecting_the_rest():
    seeds = list(range(8))
    with pytest.raises(ReplicationError) as info:
        run_replications(rf.fail_on_3_and_5, seeds, workers=2)
    err = info.value
    assert err.failed_seeds == [3, 5]
    assert "seeds: 3, 5" in str(err)
    assert "first failure, seed 3" in str(err)
    assert "ValueError: bad seed 3" in err.first_traceback
    assert isinstance(err.failures[0].exception, ValueError)
    assert err.results == [None if s in (3, 5) else s * s for s in seeds]
    assert err.unfinished == []


def test_pool_is_reused_across_map_calls_and_survives_failures():
    with ReplicationPool(workers=2) as pool:
        first = pool.map(rf.pid, range(6), chunksize=1)
        with pytest.raises(ReplicationError):
            pool.map(rf.fail_on_3_and_5, range(6))
        second = pool.map(rf.pid, range(6), chunksize=1)
        unordered = pool.map(rf.echo_slow, range(4), chunksize=1,
                             ordered=False)
    # Two worker processes served all three batches.
    assert len(set(first) | set(second)) <= 2
    assert os.getpid() not in first
    assert sorted(unordered, key=lambda p: p[0]) == [
        (s, _expected(s)) for s in range(4)]
    with pytest.raises(ValueError):
        pool.map(rf.pid, [1])


def test_default_chunksize_heuristic():
    assert default_chunksize(8, 2) == 1
    assert default_chunksize(20, 4) == 1
    assert default_chunksize(200, 12) == 4
    assert default_chunksize(200, 4) == 12
    assert default_chunksize(1000, 20) == 12
    assert default_chunksize(0, 4) == 1
    assert default_chunksize(10, 0) == 2


def test_seed_sequence_is_deterministic_unique_and_prefix_stable():
    a = seed_sequence(1, 200)
    assert a == seed_sequence(1, 200)
    assert len(set(a)) == 200
    assert all(0 <= s < 2 ** 63 for s in a)
    assert seed_sequence(1, 50) == a[:50]
    assert set(seed_sequence(2, 200)).isdisjoint(a)
    assert seed_sequence(1, 0) == []
    # Pinned values: the derivation must not change between releases.
    assert a[:3] == [3643075650177273617, 3393255045412180808,
                     1757153999920578595]
    with pytest.raises(ValueError):
        seed_sequence(1, -1)
    with pytest.raises(TypeError):
        seed_sequence(1.5, 3)


def test_nested_call_runs_sequentially_inside_the_worker():
    assert not in_replication_worker()
    out = run_replications(rf.nested, [0, 1], workers=2, chunksize=1)
    for outer_pid, inner_pids, flag in out:
        assert flag is True
        assert inner_pids == [outer_pid] * 3
        assert outer_pid != os.getpid()


def test_workers_zero_runs_in_process_with_the_same_error_policy():
    assert run_replications(rf.pid, [1, 2], workers=0) == [os.getpid()] * 2
    with pytest.raises(ReplicationError) as info:
        run_replications(rf.fail_on_3_and_5, range(6), workers=0)
    assert info.value.failed_seeds == [3, 5]


def test_unpicklable_run_is_rejected_before_starting_workers():
    with pytest.raises(TypeError, match="picklable"):
        run_replications(lambda s: s, [1, 2], workers=2)


def test_worker_exit_raises_broken_pool_naming_unfinished_seeds():
    with pytest.raises(BrokenReplicationPool) as info:
        run_replications(rf.exit_on_2, range(4), workers=1, chunksize=1)
    err = info.value
    assert 2 in err.unfinished
    assert set(err.unfinished) <= {0, 1, 2, 3}
    assert "os._exit" in str(err)
    assert len(err.results) == 4


def test_timeout_kills_workers_and_names_unfinished_seeds():
    with pytest.raises(ReplicationTimeoutError) as info:
        run_replications(rf.sleep_long, [7, 8], workers=2, chunksize=1,
                         timeout=1.0)
    assert sorted(info.value.unfinished) == [7, 8]
    assert isinstance(info.value, TimeoutError)


@pytest.mark.skipif(sys.version_info < (3, 11),
                    reason="max_tasks_per_child needs Python 3.11+")
def test_max_tasks_per_child_gives_fresh_workers():
    pids = run_replications(rf.pid_token, range(3), workers=1, chunksize=1,
                            max_tasks_per_child=1)
    assert len(set(pids)) == 3
