"""W5: the bank example (``examples/banksim``) of the checkout under test.

Builds the topology of ``examples/banksim/banksim_classic.py`` with a fixed
configuration (20 generators, queue size 10, 10 accountants, max_user
500000; the "wiq" add/remove branch is not taken), seeds the global
``random`` module and calls ``ss.simulate(1)`` ``ticks`` times.  Model
``print`` output goes to a ``StringIO``; ``os._exit`` in ``BankResult`` is
replaced by an exception so a run can never kill the process before it
reports.

The model classes come from the checkout under test, so a change to the
example models is measured together with the engine.  The parity key is the
model-level outcome (users generated / processed / dropped, queue length),
not executor transition counts: all generators share the global ``random``
stream and same-instant processing follows set iteration, so transition
counts may differ between processes while these counters stay put on a
given checkout.  If they ever differ between base and candidate the suite
refuses to compare the run.
"""

import io
import os
import random
import sys
import time
import types


class BankStop(Exception):
    """Raised instead of ``os._exit(0)`` when ``max_user`` is reached."""


def _guard_exit():
    from examples.banksim.model import model_result

    def _exit(code=0):
        raise BankStop(code)

    shim = types.SimpleNamespace(
        **{k: getattr(os, k) for k in dir(os) if not k.startswith("__")})
    shim._exit = _exit
    model_result.os = shim


def _build(p):
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from examples.banksim.model.model_accountant import BankAccountant
    from examples.banksim.model.model_queue import BankQueue
    from examples.banksim.model.model_result import BankResult
    from examples.banksim.model.model_user_gen import BankUserGenerator

    _guard_exit()
    random.seed(int(p["seed"]))
    gen_num, queue_size, proc_num = (int(p["gen_num"]), int(p["queue_size"]),
                                     int(p["proc_num"]))

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gens = []
    for i in range(gen_num):
        gen = BankUserGenerator(f"gen{i}")
        gens.append(gen)
        ss.register_entity(gen)
    que = BankQueue("Queue", queue_size, proc_num)
    ss.register_entity(que)
    accountants = []
    for i in range(proc_num):
        acc = BankAccountant("BankAccountant", i)
        accountants.append(acc)
        ss.register_entity(acc)
    result = BankResult("result", int(p["max_user"]))
    ss.register_entity(result)

    ss.insert_input_port("start")
    for gen in gens:
        ss.coupling_relation(None, "start", gen, "start")
        ss.coupling_relation(gen, "user_out", que, "user_in")
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num):
        ss.coupling_relation(que, f"proc{i}", accountants[i], "in")
        ss.coupling_relation(accountants[i], "next", que, "proc_checked")
        ss.coupling_relation(accountants[i], "next", result, "process")
    ss.insert_external_event("start", None)
    return ss, gens, que, result


def run_bank(params):
    ticks = int(params["ticks"])
    real_stdout = sys.stdout
    sink = io.StringIO()
    sys.stdout = sink
    stopped = False
    try:
        t0 = time.perf_counter()
        ss, gens, que, result = _build(params)
        t1 = time.perf_counter()
        try:
            for _ in range(ticks):
                ss.simulate(1)
        except BankStop:
            stopped = True
        t2 = time.perf_counter()
    finally:
        sys.stdout = real_stdout

    return {
        "metrics": {"sim_s": t2 - t1},
        "build_s": t1 - t0,
        "parity": {
            "generated": sum(g.generated_user for g in gens),
            "processed": result.user_count,
            "dropped": result.drop_user_count,
            "queue_len": len(que.user),
            "stopped_by_max_user": stopped,
        },
        "info": {"global_time": ss.global_time,
                 "stdout_chars": len(sink.getvalue())},
    }
