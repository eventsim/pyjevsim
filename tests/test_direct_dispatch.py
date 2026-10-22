"""``_run_instant`` calls plain ``BehaviorExecutor`` models directly.

``BehaviorExecutor`` sets ``_model_fast`` to its model when its
output/int_trans/ext_trans/con_trans wrappers are the plain forwarding
ones. These tests pin that the direct path is observably the same as the
wrappers (including ``cancel_rescheduling`` from ``ext_trans`` and
``con_trans``), and that executors with their own wrappers keep them.
"""

from pyjevsim.behavior_executor import BehaviorExecutor
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.executor import Executor
from pyjevsim.hla.hla_executor import HLAExecutor
from pyjevsim.snapshot_executor import SnapshotExecutor
from pyjevsim.structural_executor import StructuralExecutor
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class Source(BehaviorModel):
    """Emits on ``out`` every ``period``."""

    def __init__(self, name, period):
        super().__init__(name)
        self.insert_state("run", period)
        self.init_state("run")
        self.insert_output_port("out")
        self.n = 0

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self.n += 1

    def output(self, msg_deliver):
        m = SysMessage(self.get_name(), "out")
        m.insert(self.n)
        msg_deliver.insert_message(m)


class Sink(BehaviorModel):
    """Logs every transition; optionally cancels rescheduling on input."""

    def __init__(self, name, deadline, cancel, log, engine):
        super().__init__(name)
        self.insert_state("wait", deadline)
        self.init_state("wait")
        self.insert_input_port("in")
        self._cancel = cancel
        self._log = log
        self._engine = engine

    def _note(self, kind, payload=None):
        self._log.append((self._engine.get_global_time(), self.get_name(), kind, payload))

    def ext_trans(self, port, msg):
        self._note("ext", msg.retrieve()[0])
        if self._cancel:
            self.cancel_rescheduling()

    def int_trans(self):
        self._note("int")

    def con_trans(self, port_msgs):
        self._note("con", [m.retrieve()[0] for _, m in port_msgs])
        if self._cancel:
            self.cancel_rescheduling()

    def output(self, msg_deliver):
        self._note("out")


def _run(force_wrappers):
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = Source("src", 1)
    # ext only (deadline never reached between inputs), con every instant,
    # and two cancelling sinks whose cadence must survive the inputs.
    sinks = [
        Sink("ext", 2.5, False, log, ss),
        Sink("con", 1, False, log, ss),
        Sink("ext_cancel", 2.5, True, log, ss),
        Sink("con_cancel", 1, True, log, ss),
    ]
    ss.register_entity(src)
    for s in sinks:
        ss.register_entity(s)
        ss.coupling_relation(src, "out", s, "in")
    executors = [ss.get_entity(m.get_name())[0] for m in [src] + sinks]
    for ex in executors:
        assert ex._model_fast is ex.get_core_model()
        if force_wrappers:
            ex._model_fast = None
    ss.simulate(12, _tm=False)
    # Models of one instant run in set-iteration order, which follows
    # object identity; compare each model's own sequence per instant.
    return sorted(log, key=lambda entry: (entry[0], entry[1]))


def test_direct_dispatch_matches_wrappers():
    direct = _run(force_wrappers=False)
    wrapped = _run(force_wrappers=True)
    kinds = {kind for _, _, kind, _ in direct}
    assert {"ext", "int", "con", "out"} <= kinds
    assert direct == wrapped


class _Counting(BehaviorExecutor):
    calls = []

    def output(self, msg_deliver):
        self.calls.append(self.get_name())
        return super().output(msg_deliver)


def test_overriding_executor_keeps_its_wrappers():
    ex = _Counting(0, Infinite, "default", Source("s", 1), None)
    assert ex._model_fast is None
    # HLAExecutor overrides output, so it is in the same position.
    assert HLAExecutor.output is not BehaviorExecutor.output


def test_non_behavior_executors_default_to_wrappers():
    assert Executor._model_fast is None
    for cls in (SnapshotExecutor, StructuralExecutor):
        assert "_model_fast" not in vars(cls)
        assert cls._model_fast is None


def test_forcing_wrappers_on_an_instance_is_seen():
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = Source("src", 1)
    ss.register_entity(src)
    ex = ss.get_entity("src")[0]
    seen = []
    ex._model_fast = None
    ex.output = lambda md: (seen.append(ss.get_global_time()),
                            BehaviorExecutor.output(ex, md))[1]
    ss.simulate(3, _tm=False)
    assert seen == [1, 2]


class _Ticker(BehaviorModel):
    """Emits on ``out`` every tick."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("go", 1)
        self.init_state("go")
        self.insert_output_port("out")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        m = SysMessage(self.get_name(), "out")
        m.insert(self.global_time)
        msg_deliver.insert_message(m)


class _VetoingCanceller(BehaviorModel):
    """Asks for cancellation on every input but vetoes it in get_cancel_flag."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("busy", 3)
        self.init_state("busy")
        self.insert_input_port("in")
        self.ints = []

    def ext_trans(self, port, msg):
        self.cancel_rescheduling()

    def int_trans(self):
        self.ints.append(self.global_time)

    def output(self, msg_deliver):
        pass

    def get_cancel_flag(self):
        return False


def test_overridden_get_cancel_flag_is_consulted():
    # The direct path reads the cancel flag attribute, so a model that
    # overrides get_cancel_flag must stay on the wrappers, which call it.
    # Here the override vetoes every cancellation: each input restarts the
    # 3-tick busy timer, and with an input every tick it never expires.
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = _Ticker("src")
    vetoer = _VetoingCanceller("vetoer")
    ss.register_entity(src)
    ss.register_entity(vetoer)
    ss.coupling_relation(src, "out", vetoer, "in")
    assert ss.get_entity("vetoer")[0]._model_fast is None
    assert ss.get_entity("src")[0]._model_fast is src
    ss.simulate(10, _tm=False)
    assert vetoer.ints == []


def test_duck_typed_model_without_get_cancel_flag_constructs():
    class Duck:
        def get_obj_id(self):
            return 0

    ex = BehaviorExecutor(0, Infinite, "default", Duck(), None)
    assert ex._model_fast is None


class _Canceller(BehaviorModel):
    """Restarts a 3-tick busy timer on input unless it cancels rescheduling."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("busy", 3)
        self.init_state("busy")
        self.insert_input_port("in")
        self.ints = []

    def ext_trans(self, port, msg):
        self.cancel_rescheduling()

    def int_trans(self):
        self.ints.append(self.global_time)

    def output(self, msg_deliver):
        pass


def test_instance_get_cancel_flag_set_before_construction_is_consulted():
    # Same veto as above, but assigned on the instance before the executor
    # is built. BehaviorExecutor sees it in the model's __dict__ and keeps
    # the wrappers, which call it, so the timer never expires (as on main).
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = _Ticker("src")
    canceller = _Canceller("canceller")
    canceller.get_cancel_flag = lambda: False
    ss.register_entity(src)
    ss.register_entity(canceller)
    ss.coupling_relation(src, "out", canceller, "in")
    assert ss.get_entity("canceller")[0]._model_fast is None
    ss.simulate(10, _tm=False)
    assert canceller.ints == []


def test_cancel_without_override_keeps_the_timer():
    # Control for the test above: honoured cancellation keeps the 3-tick
    # cadence on the direct path.
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = _Ticker("src")
    canceller = _Canceller("canceller")
    ss.register_entity(src)
    ss.register_entity(canceller)
    ss.coupling_relation(src, "out", canceller, "in")
    assert ss.get_entity("canceller")[0]._model_fast is canceller
    ss.simulate(10, _tm=False)
    assert canceller.ints


class _Recorder(BehaviorModel):
    """Logs (name, time) for every input; passive between inputs."""

    def __init__(self, name, log):
        super().__init__(name)
        self.insert_state("idle", Infinite)
        self.init_state("idle")
        self.insert_input_port("in")
        self._log = log

    def ext_trans(self, port, msg):
        self._log.append((self.get_name(), msg.retrieve()[0]))

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass


def test_reassigning_behavior_model_with_model_fast_is_seen():
    # _model_fast binds the model at construction. Code that swaps
    # ``executor.behavior_model`` must update _model_fast as well (here to
    # None, which routes dispatch through the wrappers and so through the
    # new model).
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    src = _Ticker("src")
    old = _Recorder("k", log)
    ss.register_entity(src)
    ss.register_entity(old)
    ss.coupling_relation(src, "out", old, "in")
    ex = ss.get_entity("k")[0]
    assert ex._model_fast is old
    ss.simulate(1.5, _tm=False)
    before = len(log)
    ex.behavior_model = _Recorder("k_new", log)
    ex._model_fast = None
    ss.simulate(2, _tm=False)
    assert before and {name for name, _ in log[:before]} == {"k"}
    assert len(log) > before and {name for name, _ in log[before:]} == {"k_new"}


def test_instance_bound_method_of_another_model_keeps_the_wrappers():
    # A get_cancel_flag borrowed from another model is the base method but
    # reports that model's flag, so it must stay on the wrappers too.
    other = _Canceller("other")
    m = _Canceller("m")
    m.get_cancel_flag = other.get_cancel_flag
    ex = BehaviorExecutor(0, Infinite, "default", m, None)
    assert ex._model_fast is None
