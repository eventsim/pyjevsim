"""W3: sparse generator -> sink (the ``benchmark.run_sparse`` topology).

A periodic generator fires ``count`` times, ``period`` simulated ticks
apart, into a single sink.  Each instant carries one output and one
external transition, so the per-instant fixed cost of the V_TIME loop
dominates; this is the workload where a dense-path optimisation can show up
as a regression.
"""

import time


def run_sparse(params):
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor

    from benchmark.engines.pyjevsim.sparse import CountingSink, PeriodicGen

    count, period = int(params["count"]), params["period"]

    t0 = time.perf_counter()
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = PeriodicGen(period, count)
    sink = CountingSink()
    ss.register_entity(gen)
    ss.register_entity(sink)
    ss.coupling_relation(gen, "out", sink, "in")
    t1 = time.perf_counter()
    ss.simulate(period * count + 4, _tm=False)
    t2 = time.perf_counter()

    return {
        "metrics": {"sim_s": t2 - t1},
        "build_s": t1 - t0,
        "parity": {"fired": gen._fired, "received": sink.received,
                   "global_time": ss.global_time},
        "info": {"instants_per_s": count / (t2 - t1)},
    }
