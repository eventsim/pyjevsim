"""Tests for Parallel-DEVS confluent transitions in pyjevsim.

Before the two-phase tick rewrite the simulator interleaved each model's
output, its receivers' ext_trans, and its own int_trans inside an inner
loop. Confluent cases — where a model is both imminent and receiving an
external event at the same simulated instant — were not handled with
``δ_con``; the receiver fired one extra ``ext_trans`` and the firer's
``int_trans`` ran on a logically separate tick.

These tests pin the new behaviour: ``con_trans`` runs whenever both
triggers coincide, the default implementation is ``int_trans;ext_trans``,
and subclasses can override.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class _OneShotEmitter(BehaviorModel):
    """Fires output once at t=0 then passivates. Used to inject a seed."""

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
    """Counts every transition kind it sees and stays passive again after."""

    def __init__(self, name, log):
        super().__init__(name)
        self.insert_state("passive")
        self.insert_state("active", 0)
        self.init_state("passive")
        self.insert_input_port("in")
        self.insert_output_port("out")
        self._log = log
        self.n_int = 0
        self.n_ext = 0
        self.n_con = 0

    def ext_trans(self, port, msg):
        self.n_ext += 1
        self._log.append((self.get_name(), "ext"))
        self._cur_state = "active"

    def int_trans(self):
        self.n_int += 1
        self._log.append((self.get_name(), "int"))
        self._cur_state = "passive"

    def con_trans(self, port_msgs):
        self.n_con += 1
        self._log.append((self.get_name(), "con"))
        # Default semantics: int then ext. Equivalent here to
        # transitioning to passive and back to active.
        self._cur_state = "passive"
        for _ in port_msgs:
            self._cur_state = "active"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(1)
            msg_deliver.insert_message(m)


def test_confluent_fires_when_both_imminent_and_receiving():
    """Two atomics A and B are both imminent at t=0 (sigma=0 from the seed)
    and A's output is coupled to B. B should see ``con_trans``, not a bare
    ``ext_trans`` and a delayed ``int_trans``."""
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    seed = _OneShotEmitter()
    a = _CounterAtomic("A", log)
    b = _CounterAtomic("B", log)
    ss.register_entity(seed)
    ss.register_entity(a)
    ss.register_entity(b)

    # Seed -> both A and B (both become imminent at t=0).
    ss.coupling_relation(seed, "out", a, "in")
    ss.coupling_relation(seed, "out", b, "in")
    # A.out -> B.in so that on the next round B is again influenced
    # while still imminent.
    ss.coupling_relation(a, "out", b, "in")

    ss.simulate(5, _tm=False)

    # Round 1: both A and B become active via ext_trans from seed.
    # Round 2: A and B both imminent (sigma=0). A fires output to B.
    #          A is imminent only -> int_trans.
    #          B is imminent + receiving (from A) -> con_trans.
    assert b.n_con == 1, f"B should fire con_trans once, got {b.n_con} (log={log})"
    assert a.n_con == 0, f"A should not fire con_trans, got {a.n_con}"


def test_default_con_trans_is_int_then_ext():
    """The default ``BehaviorModel.con_trans`` must call ``int_trans``
    followed by ``ext_trans`` — matches xdevs and PythonPDEVS."""
    order = []

    class M(BehaviorModel):
        def __init__(self):
            super().__init__("m")
            self.insert_state("active", 0)
            self.init_state("active")
            self.insert_input_port("in")

        def ext_trans(self, port, msg):
            order.append("ext")

        def int_trans(self):
            order.append("int")

    m = M()
    # Synthetic bag with one fake (port, msg) pair.
    m.con_trans([("in", object())])
    assert order == ["int", "ext"]


def test_subclass_can_override_con_trans():
    """Subclasses must be able to override ``con_trans`` to provide
    custom semantics (e.g. skip int, or ext-then-int, or domain-specific)."""
    order = []

    class M(BehaviorModel):
        def __init__(self):
            super().__init__("m")
            self.insert_state("active", 0)
            self.init_state("active")
            self.insert_input_port("in")

        def ext_trans(self, port, msg):
            order.append("ext")

        def int_trans(self):
            order.append("int")

        def con_trans(self, port_msgs):
            # custom: ext-then-int
            for port, msg in port_msgs:
                self.ext_trans(port, msg)
            self.int_trans()

    m = M()
    m.con_trans([("in", object())])
    assert order == ["ext", "int"]


def test_no_confluent_when_only_imminent():
    """A model with no input bag must fire `int_trans`, never `con_trans`."""
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    a = _CounterAtomic("A", log)
    ss.register_entity(a)
    ss.insert_external_event_port_if_needed = lambda *args: None  # noop helper
    # Drive A externally — it then becomes imminent on its own at t=0.
    ss.insert_input_port("kick")
    ss.coupling_relation(None, "kick", a, "in")
    ss.insert_external_event("kick", None)

    ss.simulate(5, _tm=False)

    assert a.n_con == 0
    assert a.n_ext == 1
    # After ext_trans, A is sigma=0 -> next round int_trans.
    assert a.n_int == 1
