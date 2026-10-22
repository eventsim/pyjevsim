"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Replication functions for tests/test_replication.py.

They live in their own small module because spawn workers import the module
that defines ``run`` by name; keeping it free of pytest keeps the per-worker
import cost low.
"""
import os
import random
import time

from pyjevsim.replication import in_replication_worker, run_replications


def echo_slow(seed):
    """Later seeds finish first, so completion order differs from seed order."""
    time.sleep(0.02 * (8 - seed % 8))
    rng = random.Random(seed)
    return {"seed": seed, "draw": rng.random()}


def pid(seed):
    return os.getpid()


def fail_on_3_and_5(seed):
    if seed in (3, 5):
        raise ValueError(f"bad seed {seed}")
    return seed * seed


def exit_on_2(seed):
    if seed == 2:
        os._exit(3)
    return seed


def sleep_long(seed):
    time.sleep(30)
    return seed


def nested(seed):
    inner = run_replications(pid, [1, 2, 3], workers=4)
    return os.getpid(), inner, in_replication_worker()
