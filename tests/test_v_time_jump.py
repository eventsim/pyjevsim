"""Correctness tests for V_TIME jump-to-next-event scheduling.

These cover the change in `SysExecutor.schedule()` that replaces the
fixed-`time_resolution` increment with a hop to the next scheduled event.
The tests assert two properties:

1. Events fire at the *correct simulated time*, even when the inter-event
   gap is much larger than `time_resolution`.
2. The wall-clock time stays bounded by the event count, not the simulated
   horizon — which is the whole point of jump scheduling.
"""

import time

import pytest

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class PeriodicGen(BehaviorModel):
    """Fires `count` events spaced by `period` simulated ticks.

    Logs the simulator's `global_time` at each int_trans by reading it from
    the back-reference `_ss`. We do this because pyjevsim's per-model
    `self.global_time` is updated *after* the transition and therefore
    reflects the previous activation time — not what we want for assertion.
    """

    def __init__(self, period, count, log, ss_ref):
        super().__init__("gen")
        self.insert_state("active", period)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("out")
        self._count = count
        self._fired = 0
        self._log = log
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._fired += 1
            self._log.append(self._ss.global_time)
            if self._fired >= self._count:
                self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(self._fired)
            msg_deliver.insert_message(m)


class CountingSink(BehaviorModel):
    def __init__(self, log, ss_ref):
        super().__init__("sink")
        self.insert_state("passive")
        self.init_state("passive")
        self.insert_input_port("in")
        self._log = log
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        if port == "in":
            self._log.append(self._ss.global_time)

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass


def _build(period, count):
    gen_log = []
    sink_log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = PeriodicGen(period, count, gen_log, ss)
    sink = CountingSink(sink_log, ss)
    ss.register_entity(gen)
    ss.register_entity(sink)
    ss.coupling_relation(gen, "out", sink, "in")
    return ss, gen_log, sink_log


def test_fires_at_correct_simulated_time_with_short_period():
    ss, gen_log, sink_log = _build(period=1, count=5)
    ss.simulate(20, _tm=False)
    assert gen_log == [1, 2, 3, 4, 5]
    assert sink_log == [1, 2, 3, 4, 5]


def test_fires_at_correct_simulated_time_with_long_period():
    """Period 1000 with 3 events: must fire at 1000, 2000, 3000."""
    ss, gen_log, sink_log = _build(period=1000, count=3)
    ss.simulate(5000, _tm=False)
    assert gen_log == [1000, 2000, 3000]
    assert sink_log == [1000, 2000, 3000]


def test_long_horizon_stays_fast():
    """100 events at period 1000 should run in well under 100 ms wall time.
    Old fixed-tick behaviour took >180 ms for this same configuration."""
    ss, gen_log, sink_log = _build(period=1000, count=100)
    t0 = time.perf_counter()
    ss.simulate(120_000, _tm=False)
    elapsed = time.perf_counter() - t0
    assert len(gen_log) == 100
    assert len(sink_log) == 100
    # Generous bound — the old code took ~180 ms; jump scheduling takes <2 ms.
    assert elapsed < 0.05, f"simulation wall time {elapsed:.4f}s exceeds budget"


def test_simulate_horizon_clips_correctly():
    """If target_time is reached before the generator is done, only events
    scheduled strictly before target_time should fire."""
    ss, gen_log, sink_log = _build(period=10, count=10)
    # target_time becomes 25 — events at t=10, 20 should fire; t=30 should not.
    ss.simulate(25, _tm=False)
    assert gen_log == [10, 20]


def test_non_integer_time_advance():
    """A model with sigma=2.5 should fire at 2.5, 5.0, 7.5 — not delayed
    to integer ticks as the old fixed-resolution loop would have done."""

    class FractionalGen(BehaviorModel):
        def __init__(self, log, ss_ref):
            super().__init__("gen")
            self.insert_state("active", 2.5)
            self.insert_state("done")
            self.init_state("active")
            self.insert_output_port("out")
            self.fired = 0
            self._log = log
            self._ss = ss_ref

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            if self._cur_state == "active":
                self.fired += 1
                self._log.append(self._ss.global_time)
                if self.fired >= 3:
                    self._cur_state = "done"

        def output(self, md):
            if self._cur_state == "active":
                m = SysMessage(self.get_name(), "out")
                m.insert(self.fired)
                md.insert_message(m)

    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ss.register_entity(FractionalGen(log, ss))
    ss.simulate(20, _tm=False)
    assert log == pytest.approx([2.5, 5.0, 7.5])
