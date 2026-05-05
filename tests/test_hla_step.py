"""Tests for the HLA-mode ``SysExecutor.step(granted_time)`` API.

These tests pin the contract expected by an HLA federate ambassador
that drives pyjevsim under an IEEE 1516-2010 RTI:

  * `step(granted_time)` advances `global_time` to event times within
    the grant window, not just to `granted_time` itself.
  * Multiple cascade rounds at the same simulated instant complete
    inside one `step()` call.
  * Confluent transitions (`δ_con`) fire correctly when a model is
    both imminent and receiving an internal coupled event at the
    same instant — same fix as the V_TIME path.
  * `step()` returns the output events drained during this grant so
    the federate can republish them as RTI interactions.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class _OneShotEmitter(BehaviorModel):
    """Fires once at t=0 then passivates."""

    def __init__(self, name="seed"):
        super().__init__(name)
        self.insert_state("active", 0)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("out")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(1)
            msg_deliver.insert_message(m)


class _CounterAtomic(BehaviorModel):
    """Counts every kind of transition it sees."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("passive")
        self.insert_state("active", 0)
        self.init_state("passive")
        self.insert_input_port("in")
        self.insert_output_port("out")
        self.n_int = 0
        self.n_ext = 0
        self.n_con = 0

    def ext_trans(self, port, msg):
        self.n_ext += 1
        self._cur_state = "active"

    def int_trans(self):
        self.n_int += 1
        self._cur_state = "passive"

    def con_trans(self, port_msgs):
        self.n_con += 1
        self._cur_state = "passive"
        for _ in port_msgs:
            self._cur_state = "active"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(1)
            msg_deliver.insert_message(m)


def _setup_hla(*entities, couplings=()):
    se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME, snapshot_manager=None)
    for ent in entities:
        se.register_entity(ent)
    for src, src_port, dst, dst_port in couplings:
        se.coupling_relation(src, src_port, dst, dst_port)
    se.init_sim()
    return se


def test_step_fires_confluent_transition():
    """When a model is both imminent (sigma=0 from the seed) and
    receives an internal coupled event in the same round, the new
    `step()` must invoke `con_trans`, not a separate `ext_trans`."""
    seed = _OneShotEmitter()
    a = _CounterAtomic("A")
    b = _CounterAtomic("B")

    se = _setup_hla(seed, a, b, couplings=[
        (seed, "out", a, "in"),
        (seed, "out", b, "in"),
        (a,    "out", b, "in"),
    ])

    se.step(granted_time=5.0)

    assert b.n_con == 1, (
        f"B should fire con_trans once; counts: int={b.n_int}, ext={b.n_ext}, con={b.n_con}"
    )
    assert a.n_con == 0


def test_step_advances_global_time_inside_grant_window():
    """If the next scheduled event is at t=3 and the grant is t=10,
    the event must fire while `ss.global_time == 3` (so models observe
    correct simulated time during their transition). Per IEEE 1516-2010,
    `global_time` lands at the grant boundary (10) after the step
    returns."""
    fired_at = []

    class _DelayedAtomic(BehaviorModel):
        def __init__(self, name, delay, ss_ref):
            super().__init__(name)
            self.insert_state("active", delay)
            self.insert_state("done")
            self.init_state("active")
            self.insert_output_port("out")
            self._ss = ss_ref

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            if self._cur_state == "active":
                fired_at.append(self._ss.global_time)
                self._cur_state = "done"

        def output(self, md):
            if self._cur_state == "active":
                m = SysMessage(self.get_name(), "out")
                m.insert(1)
                md.insert_message(m)

    se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME, snapshot_manager=None)
    se.register_entity(_DelayedAtomic("A", delay=3.0, ss_ref=se))
    se.init_sim()

    se.step(granted_time=10.0)

    assert fired_at == [3.0], (
        f"event should have fired at simulated time 3.0, got {fired_at}"
    )
    assert se.global_time == 10.0, (
        f"after the grant, global_time should equal granted_time 10.0; got {se.global_time}"
    )


def test_step_drains_multiple_rounds_at_same_instant():
    """Cascading sigma=0 chain should complete within one `step()`
    call, not require multiple calls per simulated instant."""
    # seed -> A -> B -> C; everything sigma=0 so the whole chain
    # propagates at t=0. After step(0), all three should have been
    # activated and passivated.
    seed = _OneShotEmitter()
    a = _CounterAtomic("A")
    b = _CounterAtomic("B")
    c = _CounterAtomic("C")
    se = _setup_hla(seed, a, b, c, couplings=[
        (seed, "out", a, "in"),
        (a,    "out", b, "in"),
        (b,    "out", c, "in"),
    ])

    se.step(granted_time=1.0)

    # Each atomic does at least one ext + one int (or one con).
    for atomic in (a, b, c):
        total = atomic.n_int + atomic.n_ext + atomic.n_con
        assert total >= 2, (
            f"{atomic.get_name()} did not complete its cascade: "
            f"int={atomic.n_int}, ext={atomic.n_ext}, con={atomic.n_con}"
        )


def test_step_returns_output_events_for_publish():
    """`step()` returns the output_event_queue contents drained during
    the step, so a federate can republish them via the RTI."""
    class _RootEmitter(BehaviorModel):
        def __init__(self):
            super().__init__("root_emitter")
            self.insert_state("active", 0)
            self.insert_state("done")
            self.init_state("active")
            self.insert_output_port("hla_out")

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            if self._cur_state == "active":
                self._cur_state = "done"

        def output(self, md):
            if self._cur_state == "active":
                m = SysMessage(self.get_name(), "hla_out")
                m.insert("payload")
                md.insert_message(m)

    em = _RootEmitter()
    se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME, snapshot_manager=None)
    se.register_entity(em)
    se.insert_output_port("hla_out")
    # Couple the model's hla_out to the simulator's external output port
    # so the message reaches the output_event_queue.
    se.coupling_relation(em, "hla_out", None, "hla_out")
    se.init_sim()

    events = se.step(granted_time=1.0)
    assert len(events) == 1
