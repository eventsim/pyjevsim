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
