"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Independent replications of the bank example with pyjevsim's replication
runner.

Each replication builds the topology of ``banksim_classic.py`` (20
generators, a queue of 10, 10 accountants), seeds the global ``random``
module from its own seed, advances ``ticks`` simulated time units and returns
the final counters.  The script runs the same seeds once sequentially in
this process and once with ``run_replications`` and prints both wall times
and the speed-up.

Usage (from the repository root or from examples/banksim)::

    python examples/banksim/banksim_replications.py --seeds 20 --workers 4

``run_bank`` is defined at module top level and the script body is guarded
by ``if __name__ == "__main__":``.  Both are required: spawn workers import
this file by path to find ``run_bank`` and must not re-run the experiment.

``BankResult`` calls ``os._exit`` once ``max_user`` users are served.  The
default horizon (3000 ticks, about 5,400 users) stays well below
``MAX_USER``; a replication that reached it would kill its worker and the
runner would raise ``BrokenReplicationPool`` naming the unfinished seeds.
"""
import argparse
import functools
import os
import random
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "../..")))

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim import run_replications, seed_sequence  # noqa: E402
from pyjevsim.replication import default_workers  # noqa: E402

from examples.banksim.model.model_accountant import BankAccountant  # noqa: E402
from examples.banksim.model.model_queue import BankQueue  # noqa: E402
from examples.banksim.model.model_result import BankResult  # noqa: E402
from examples.banksim.model.model_user_gen import BankUserGenerator  # noqa: E402

# Same configuration as scenario.yaml.
GEN_NUM = 20
QUEUE_SIZE = 10
PROC_NUM = 10
MAX_USER = 500000


def run_bank(seed, ticks=3000):
    """One replication: build, seed, simulate ``ticks`` time units, report."""
    random.seed(seed)
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    gens = []
    for i in range(GEN_NUM):
        gen = BankUserGenerator(f"gen{i}")
        gens.append(gen)
        ss.register_entity(gen)
    que = BankQueue("Queue", QUEUE_SIZE, PROC_NUM)
    ss.register_entity(que)
    accountants = []
    for i in range(PROC_NUM):
        acc = BankAccountant("BankAccountant", i)
        accountants.append(acc)
        ss.register_entity(acc)
    result = BankResult("result", MAX_USER)
    ss.register_entity(result)

    ss.insert_input_port("start")
    for gen in gens:
        ss.coupling_relation(None, "start", gen, "start")
        ss.coupling_relation(gen, "user_out", que, "user_in")
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(PROC_NUM):
        ss.coupling_relation(que, f"proc{i}", accountants[i], "in")
        ss.coupling_relation(accountants[i], "next", que, "proc_checked")
        ss.coupling_relation(accountants[i], "next", result, "process")
    ss.insert_external_event("start", None)

    for _ in range(ticks):
        ss.simulate(1)

    return {
        "seed": seed,
        "generated": sum(g.generated_user for g in gens),
        "processed": result.user_count,
        "dropped": result.drop_user_count,
        "queue_len": len(que.user),
    }


def _mean(values):
    return sum(values) / len(values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--seeds", type=int, default=20,
                        help="number of replications (default 20)")
    parser.add_argument("--workers", type=int, default=None,
                        help="worker processes (default: CPU count)")
    parser.add_argument("--ticks", type=int, default=3000,
                        help="simulated time units per replication "
                             "(default 3000)")
    parser.add_argument("--base-seed", type=int, default=1,
                        help="master seed for seed_sequence (default 1)")
    parser.add_argument("--chunksize", type=int, default=None,
                        help="replications per task (default: heuristic)")
    args = parser.parse_args(argv)

    seeds = seed_sequence(args.base_seed, args.seeds)
    run = functools.partial(run_bank, ticks=args.ticks)
    workers = args.workers if args.workers is not None else default_workers()

    t0 = time.perf_counter()
    sequential = [run(seed) for seed in seeds]
    t_seq = time.perf_counter() - t0

    t0 = time.perf_counter()
    parallel = run_replications(run, seeds, workers=workers,
                                chunksize=args.chunksize)
    t_par = time.perf_counter() - t0

    same = sum(a == b for a, b in zip(sequential, parallel))
    print(f"bank example: {len(seeds)} replications x {args.ticks} ticks, "
          f"{workers} workers (os.cpu_count()={os.cpu_count()})")
    print(f"  sequential      : {t_seq:7.3f} s "
          f"({t_seq / len(seeds) * 1000:.1f} ms per replication)")
    print(f"  run_replications: {t_par:7.3f} s (includes pool start-up)")
    print(f"  speed-up        : {t_seq / t_par:7.2f}x")
    print(f"  mean processed {_mean([r['processed'] for r in parallel]):.1f}, "
          f"mean dropped {_mean([r['dropped'] for r in parallel]):.1f}")
    print(f"  identical counters in both runs: {same}/{len(seeds)} seeds "
          f"(bit-reproducibility across processes is not guaranteed yet)")


if __name__ == "__main__":
    main()
