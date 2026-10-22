"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Call-count budget for the simulation loop (roadmap INF-11).

Wall-clock gates are noisy (+-5-20% on a shared machine); the number of
calls the engine makes per transition is not.  These tests count the
Python-level function starts and the calls into C made while
``SysExecutor.simulate()`` runs (model build excluded), divide by the number
of model transitions, and fail when a count exceeds the budget: the value
measured on main at ``BUDGET_COMMIT`` plus ``MARGIN``.

Counting uses ``sys.monitoring`` on Python 3.12+ (``PY_START`` for Python
function starts; ``CALL`` events whose callable is not a Python function or
bound method for C calls) and ``sys.setprofile`` before 3.12 (``call`` and
``c_call``).  The two do not count the same things, and bytecode differs
between interpreter versions, so budgets are recorded per version in
``MEASURED``; a version without an entry skips.

When an engine change legitimately moves a count (a new feature on the hot
path), update ``MEASURED`` and ``BUDGET_COMMIT`` in the same PR and say so
in the PR description.  Print the current values with::

    python -m tests.test_call_budget
"""

import sys
import types

import pytest

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage

from .model_bank_accountant import BankAccountant
from .model_bank_queue import BankQueue
from .model_bank_user_gen import BankUserGenerator

# Raw counts measured on main at BUDGET_COMMIT, per interpreter version:
# workload -> (Python calls, C calls, transitions).  The budget for each
# kind is calls / transitions * MARGIN.
#
# Python-level calls and transitions are identical on 3.11-3.14 and in every
# run.  C calls are not: the bucket cache in ScheduleQueue.reschedule_all
# hits or misses (one dict.get) depending on the iteration order of the
# affected-model set, which follows object identity, so they spread by up
# to 2.4% over 30 runs.  The C values below are the maximum of 30 runs, so
# the C budget catches increases of more than about 3%, and the Python
# budget is the sharp one.  Measured on Windows 11 (the counts do not
# depend on the platform).  Python 3.10 has no recorded budget and skips.
BUDGET_COMMIT = "f7145e6"
MARGIN = 1.03

MEASURED = {
    (3, 11): {  # CPython 3.11.15, sys.setprofile counting
        "bank_flat": (6870, 7714, 864),
        "devstone_hi_6x8_10": (14939, 17256, 2830),
    },
    (3, 12): {  # CPython 3.12.13
        "bank_flat": (6870, 9782, 864),
        "devstone_hi_6x8_10": (14939, 20397, 2830),
    },
    (3, 13): {  # CPython 3.13.13
        "bank_flat": (6870, 9782, 864),
        "devstone_hi_6x8_10": (14939, 20417, 2830),
    },
    (3, 14): {  # CPython 3.14.0
        "bank_flat": (6870, 9782, 864),
        "devstone_hi_6x8_10": (14939, 20407, 2830),
    },
}

_PY_FUNCS = (types.FunctionType, types.MethodType)


# --------------------------------------------------------------------------
# Workloads (frozen copies: editing benchmark/ must not move the budget)
# --------------------------------------------------------------------------

class _Atomic(BehaviorModel):
    """DEVStone atomic: passive; on input become active (deadline 0)."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("passive")
        self.insert_state("active", 0)
        self.init_state("passive")
        self.insert_input_port("in")
        self.insert_output_port("out")
        self.n = 0

    def ext_trans(self, port, msg):
        self.n += 1
        self._cur_state = "active"

    def int_trans(self):
        self.n += 1
        self._cur_state = "passive"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "out")
        msg.insert(0)
        msg_deliver.insert_message(msg)


class _Seeder(BehaviorModel):
    """Fires ``events`` seeds at t = 0, 1, 2, ..."""

    def __init__(self, events):
        super().__init__("seeder")
        self.insert_state("active", 0)
        self.insert_state("wait", 1)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("out")
        self.remaining = events

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self.remaining -= 1
        self._cur_state = "wait" if self.remaining > 0 else "done"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "out")
        msg.insert(0)
        msg_deliver.insert_message(msg)


def build_devstone_hi(depth=6, width=8, events=10):
    """Flattened DEVStone HI (the benchmark adapter's shape)."""
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    seeder = _Seeder(events)
    ss.register_entity(seeder)
    levels = []
    for d, count in enumerate([1] + [width - 1] * (depth - 1)):
        row = [_Atomic(f"a_d{d}_i{i}") for i in range(count)]
        for atomic in row:
            ss.register_entity(atomic)
            ss.coupling_relation(seeder, "out", atomic, "in")
        levels.append(row)
    for row in levels[1:]:
        for a, b in zip(row, row[1:]):
            ss.coupling_relation(a, "out", b, "in")
    atomics = [a for row in levels for a in row]
    horizon = (events - 1) + max(8, depth * width + 4)

    def run():
        ss.simulate(horizon, _tm=False)

    # The seeder's own transitions are counted too (one int_trans per seed).
    return (run, (_Atomic, _Seeder),
            lambda: sum(a.n for a in atomics) + events)


def build_bank(gen_num=4, gen_cycle=1, users_per_gen=60, proc_num=3,
               queue_size=5, proc_time=2):
    """Flat bank topology of tests/test_banksim.py, sized so users drop."""
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gens = [BankUserGenerator(f"gen{i}", gen_cycle, users_per_gen, proc_time)
            for i in range(gen_num)]
    for gen in gens:
        ss.register_entity(gen)
    que = BankQueue("Queue", queue_size, proc_num)
    ss.register_entity(que)
    accountants = [BankAccountant("BankAccountant", i) for i in range(proc_num)]
    for acc in accountants:
        ss.register_entity(acc)
    ss.insert_input_port("start")
    for gen in gens:
        ss.coupling_relation(None, "start", gen, "start")
        ss.coupling_relation(gen, "user_out", que, "user_in")
    for i, acc in enumerate(accountants):
        ss.coupling_relation(que, f"proc{i}", acc, "in")
        ss.coupling_relation(acc, "next", que, "proc_checked")
    ss.insert_external_event("start", None)
    horizon = gen_cycle * users_per_gen + proc_time * 4 * gen_num + 10

    def run():
        ss.simulate(horizon, _tm=False)

    return run, (BankUserGenerator, BankQueue, BankAccountant), None


WORKLOADS = {
    "devstone_hi_6x8_10": build_devstone_hi,
    "bank_flat": build_bank,
}


# --------------------------------------------------------------------------
# Counting
# --------------------------------------------------------------------------

def _transition_codes(classes):
    codes = set()
    for cls in classes:
        for name in ("int_trans", "ext_trans"):
            func = cls.__dict__.get(name)
            if func is not None:
                codes.add(func.__code__)
    return codes


def _count_monitoring(run, codes):
    mon = sys.monitoring
    events = mon.events
    tool = None
    for candidate in (5, 4, 3, 2, 1):
        try:
            mon.use_tool_id(candidate, "pyjevsim-call-budget")
        except ValueError:
            continue
        tool = candidate
        break
    if tool is None:
        pytest.skip("no free sys.monitoring tool id")
    counts = [0, 0, 0]

    def on_start(code, offset):
        counts[0] += 1
        if code in codes:
            counts[2] += 1

    def on_call(code, offset, callable_, arg0):
        if not isinstance(callable_, _PY_FUNCS):
            counts[1] += 1

    mon.register_callback(tool, events.PY_START, on_start)
    mon.register_callback(tool, events.CALL, on_call)
    try:
        mon.set_events(tool, events.PY_START | events.CALL)
        run()
    finally:
        mon.set_events(tool, 0)
        mon.register_callback(tool, events.PY_START, None)
        mon.register_callback(tool, events.CALL, None)
        mon.free_tool_id(tool)
    return tuple(counts)


def _count_setprofile(run, codes):
    # Python < 3.12: "call" also fires when a generator resumes, and
    # comprehensions run in frames of their own, so these counts are not
    # comparable with the sys.monitoring ones.
    counts = [0, 0, 0]

    def prof(frame, event, arg):
        if event == "call":
            counts[0] += 1
            if frame.f_code in codes:
                counts[2] += 1
        elif event == "c_call":
            counts[1] += 1

    old = sys.getprofile()
    sys.setprofile(prof)
    try:
        run()
    finally:
        sys.setprofile(old)
    return tuple(counts)


def count_calls(run, classes):
    """Return (python_calls, c_calls, transitions) made while ``run()`` runs.

    Transitions are the starts of the workload classes' own ``int_trans``
    and ``ext_trans`` (a confluent transition counts as one ``int_trans``
    plus one ``ext_trans`` per input, as ``BehaviorModel.con_trans`` does).
    """
    codes = _transition_codes(classes)
    if hasattr(sys, "monitoring"):
        return _count_monitoring(run, codes)
    return _count_setprofile(run, codes)


def measure(name):
    run, classes, model_count = WORKLOADS[name]()
    py, c, transitions = count_calls(run, classes)
    if model_count is not None:
        assert transitions == model_count(), (transitions, model_count())
    assert transitions > 0
    return {"py": py / transitions, "c": c / transitions,
            "transitions": transitions, "py_calls": py, "c_calls": c}


def _recorded(name):
    recorded = MEASURED.get(sys.version_info[:2], {}).get(name)
    if recorded is None:
        pytest.skip(f"no call budget recorded for Python "
                    f"{sys.version_info[0]}.{sys.version_info[1]}")
    return recorded


@pytest.mark.parametrize("name", sorted(WORKLOADS))
def test_calls_per_transition_within_budget(name):
    py_calls, c_calls, transitions = _recorded(name)
    got = measure(name)
    assert got["transitions"] == transitions, (
        f"{name}: {got['transitions']} transitions, the budget was measured "
        f"on {transitions}; the workload or the model semantics changed, "
        f"re-measure MEASURED")
    for kind, calls in (("py", py_calls), ("c", c_calls)):
        base = calls / transitions
        budget = base * MARGIN
        assert got[kind] <= budget, (
            f"{name}: {got[kind]:.3f} {kind} calls per transition exceeds the "
            f"budget {budget:.3f} ({base:.3f} measured at {BUDGET_COMMIT} "
            f"+ {MARGIN - 1:.0%}). If the increase is intended, update "
            f"MEASURED in tests/test_call_budget.py.")


def test_call_counts_are_repeatable():
    # The same workload twice in one process with fresh models: Python-level
    # calls and transitions match exactly; C calls stay within MARGIN (see
    # the note on MEASURED).
    a = measure("devstone_hi_6x8_10")
    b = measure("devstone_hi_6x8_10")
    assert (a["py_calls"], a["transitions"]) == (b["py_calls"], b["transitions"])
    assert abs(a["c_calls"] - b["c_calls"]) <= (MARGIN - 1) * a["c_calls"]


if __name__ == "__main__":
    print(f"Python {sys.version.split()[0]} "
          f"({'sys.monitoring' if hasattr(sys, 'monitoring') else 'setprofile'})")
    for _name in sorted(WORKLOADS):
        _m = measure(_name)
        print(f'    "{_name}": ({_m["py_calls"]}, {_m["c_calls"]}, '
              f'{_m["transitions"]}),  # py {_m["py"]:.4f} c {_m["c"]:.4f} '
              f'per transition')
