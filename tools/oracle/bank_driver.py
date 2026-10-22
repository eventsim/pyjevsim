"""Bank-simulation driver used for both benchmarking and the trace oracle.

Builds exactly the topology of ``examples/banksim/banksim_classic.py`` (the
"wiq" generator add/remove branch is not taken, i.e. wiq_gen_num == gen_num),
with the configuration read from ``examples/banksim/scenario.yaml`` of the
checkout under test, seeds the global ``random`` module, and calls
``ss.simulate(1)`` ``--ticks`` times (default 3000).  Model ``print`` output is
redirected to a StringIO, and ``os._exit`` inside ``model_result`` is replaced
by an exception so a run can never kill the process.

Usage (benchmark, run from anywhere):

    python tools/oracle/bank_driver.py --repo <checkout> [--ticks 3000] [--seed 1] [--count-transitions]

It prints one JSON line on stdout: elapsed wall time of the simulate loop
plus outcome counters (users generated / processed / dropped, queue length,
final time).  ``--count-transitions`` additionally wraps the executor
transition methods with counters (adds overhead; use it for verification
runs, not for timing).

NOTE: this raw example is ORDER-SENSITIVE: all generators share the global
``random`` stream and the queue's FIFO order follows the bag order, so its
outcome counters depend on the engine's same-time processing order (set
iteration).  An engine change that legitimately alters that order can change
these counters without being a semantic regression.  The trace oracle's
``bank_canon`` scenario is the order-insensitive variant.
"""

import argparse
import io
import json
import os
import random
import sys
import time
import types


class BankStop(Exception):
    """Raised instead of os._exit(0) by BankResult when max_user is reached."""


def _read_config(repo):
    path = os.path.join(repo, "examples", "banksim", "scenario.yaml")
    cfg = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            cfg[k.strip()] = int(v.strip())
    return cfg


def guard_exit():
    """Make BankResult's os._exit raise BankStop instead of killing the process."""
    from examples.banksim.model import model_result

    def _exit(code=0):
        raise BankStop(code)

    shim = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")})
    shim._exit = _exit
    model_result.os = shim


def build_bank(repo, seed=1):
    """Build the bank simulation. Returns (ss, handles)."""
    random.seed(seed)
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from examples.banksim.model.model_accountant import BankAccountant
    from examples.banksim.model.model_queue import BankQueue
    from examples.banksim.model.model_user_gen import BankUserGenerator
    from examples.banksim.model.model_result import BankResult

    guard_exit()
    cfg = _read_config(repo)
    gen_num, queue_size, proc_num, max_user = (
        cfg["gen_num"], cfg["queue_size"], cfg["proc_num"], cfg["max_user"])

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen_list = []
    for i in range(gen_num):
        gen = BankUserGenerator(f"gen{i}")
        gen_list.append(gen)
        ss.register_entity(gen)
    que = BankQueue("Queue", queue_size, proc_num)
    ss.register_entity(que)
    account_list = []
    for i in range(proc_num):
        account = BankAccountant("BankAccountant", i)
        account_list.append(account)
        ss.register_entity(account)
    result = BankResult("result", max_user)
    ss.register_entity(result)

    ss.insert_input_port("start")
    for gen in gen_list:
        ss.coupling_relation(None, "start", gen, "start")
        ss.coupling_relation(gen, "user_out", que, "user_in")
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num):
        ss.coupling_relation(que, f"proc{i}", account_list[i], "in")
        ss.coupling_relation(account_list[i], "next", que, "proc_checked")
        ss.coupling_relation(account_list[i], "next", result, "process")
    ss.insert_external_event("start", None)
    return ss, {"gens": gen_list, "queue": que, "accountants": account_list,
                "result": result, "cfg": cfg}


def run_bank(ss, ticks, on_tick=None):
    """Call ss.simulate(1) `ticks` times. Returns True if BankStop fired."""
    try:
        for k in range(ticks):
            ss.simulate(1)
            if on_tick is not None:
                on_tick(k)
    except BankStop:
        return True
    return False


def outcome(ss, h, stopped):
    q, r = h["queue"], h["result"]
    return {
        "global_time": ss.global_time,
        "generated": sum(g.generated_user for g in h["gens"]),
        "processed": r.user_count,
        "dropped": r.drop_user_count,
        "queue_len": len(q.user),
        "queue_dropped_pending": len(q.dropped_user),
        "usable_proc": len(q.usable_proc),
        "stopped_by_max_user": stopped,
    }


def install_transition_counter():
    """Count model-level transitions (wraps every BehaviorModel subclass)."""
    from pyjevsim.behavior_model import BehaviorModel
    counts = {"output": 0, "int_trans": 0, "ext_trans": 0, "con_trans": 0}

    def wrap(cls, name):
        f = cls.__dict__.get(name)
        if f is None or getattr(f, "_bank_counted", False):
            return

        def w(self, *a, **k):
            counts[name] += 1
            return f(self, *a, **k)
        w._bank_counted = True
        setattr(cls, name, w)

    stack = [BehaviorModel]
    seen = set()
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(c.__subclasses__())
        for n in counts:
            wrap(c, n)
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", required=True)
    p.add_argument("--ticks", type=int, default=3000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--count-transitions", action="store_true")
    a = p.parse_args(argv)
    repo = os.path.abspath(a.repo)
    sys.path.insert(0, repo)
    import pyjevsim
    assert os.path.abspath(pyjevsim.__file__).startswith(repo), pyjevsim.__file__

    real_stdout = sys.stdout
    sink = io.StringIO()
    sys.stdout = sink
    try:
        ss, h = build_bank(repo, a.seed)
        counts = install_transition_counter() if a.count_transitions else None
        t0 = time.perf_counter()
        stopped = run_bank(ss, a.ticks)
        elapsed = time.perf_counter() - t0
    finally:
        sys.stdout = real_stdout
    res = {"elapsed_s": round(elapsed, 6), "ticks": a.ticks, "seed": a.seed}
    res.update(outcome(ss, h, stopped))
    if counts is not None:
        res["transitions"] = counts["int_trans"] + counts["ext_trans"] + counts["con_trans"]
        res["model_calls"] = counts
    res["stdout_chars"] = len(sink.getvalue())
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
