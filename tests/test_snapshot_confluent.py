"""SnapshotExecutor in confluent instants and the state its hooks receive.

A snapshot-decorated model that is imminent and receiving at the same
instant used to raise AttributeError (SnapshotExecutor had no con_trans),
and every SnapshotCondition hook received ``cur_state == ""`` because the
executor reported its own, never-updated state instead of the model's.
"""

import os

import dill

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType
from pyjevsim.snapshot_condition import SnapshotCondition
from pyjevsim.snapshot_executor import SnapshotExecutor
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class _Seed(BehaviorModel):
    """Emits one message at t=0, then passivates."""

    def __init__(self):
        super().__init__("seed")
        self.insert_state("active", 0)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("out")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            msg = SysMessage(self.get_name(), "out")
            msg.insert(1)
            msg_deliver.insert_message(msg)


class _Relay(BehaviorModel):
    """Becomes active on input, emits once, then passivates.

    Uses the default con_trans (int_trans, then ext_trans per message).
    """

    def __init__(self, name, log):
        super().__init__(name)
        self.insert_state("passive")
        self.insert_state("active", 0)
        self.init_state("passive")
        self.insert_input_port("in")
        self.insert_output_port("out")
        self._log = log

    def ext_trans(self, port, msg):
        self._log.append((self.get_name(), "ext"))
        self._cur_state = "active"

    def int_trans(self):
        self._log.append((self.get_name(), "int"))
        self._cur_state = "passive"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            msg = SysMessage(self.get_name(), "out")
            msg.insert(1)
            msg_deliver.insert_message(msg)


class _RecordingCondition(SnapshotCondition):
    """Records every hook call; snapshots on the hooks named in ``fire``."""

    calls = []
    fire = {}

    @staticmethod
    def create_executor(behavior_executor):
        return _RecordingCondition(behavior_executor)

    def _hook(self, name, cur_state):
        _RecordingCondition.calls.append((name, cur_state))
        return _RecordingCondition.fire.get(name) == cur_state

    def snapshot_time_condition(self, global_time):
        return False

    def snapshot_pre_condition_ext(self, port, msg, cur_state):
        return self._hook("pre_ext", cur_state)

    def snapshot_post_condition_ext(self, port, msg, cur_state):
        return self._hook("post_ext", cur_state)

    def snapshot_pre_condition_int(self, cur_state):
        return self._hook("pre_int", cur_state)

    def snapshot_post_condition_int(self, cur_state):
        return self._hook("post_int", cur_state)

    def snapshot_pre_condition_out(self, cur_state):
        return self._hook("pre_out", cur_state)

    def snapshot_post_condition_out(self, msg, cur_state):
        return self._hook("post_out", cur_state)


def _run(tmp_path, monkeypatch, fire=None):
    """seed -> A, B and A -> B: at t=0 B is imminent and receives from A."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_RecordingCondition, "calls", [])
    monkeypatch.setattr(_RecordingCondition, "fire", dict(fire or {}))

    log = []
    sm = SnapshotManager()
    sm.register_snapshot_condition("B", _RecordingCondition.create_executor)
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=sm)
    seed, a, b = _Seed(), _Relay("A", log), _Relay("B", log)
    for m in (seed, a, b):
        se.register_entity(m)
    se.coupling_relation(seed, "out", a, "in")
    se.coupling_relation(seed, "out", b, "in")
    se.coupling_relation(a, "out", b, "in")

    se.simulate(3, _tm=False)

    assert isinstance(se.product_port_map[b], SnapshotExecutor)
    return log, _RecordingCondition.calls, se


def test_confluent_instant_runs_default_con_trans(tmp_path, monkeypatch):
    log, _, se = _run(tmp_path, monkeypatch)

    b_log = [kind for name, kind in log if name == "B"]
    # ext from seed; con (int, then ext from A); int after B's own output.
    assert b_log == ["ext", "int", "ext", "int"]
    assert se.get_model("B")._cur_state == "passive"


def test_hooks_order_and_states_in_confluent_instant(tmp_path, monkeypatch):
    _, calls, _ = _run(tmp_path, monkeypatch)

    assert calls == [
        # Round 1: B receives from seed.
        ("pre_ext", "passive"), ("post_ext", "active"),
        # Round 2: B emits, then is imminent and receiving from A. The
        # int hooks bracket the confluent transition; no ext hooks fire.
        ("pre_out", "active"), ("post_out", "active"),
        ("pre_int", "active"), ("post_int", "active"),
        # Round 3: B emits and passivates.
        ("pre_out", "active"), ("post_out", "active"),
        ("pre_int", "active"), ("post_int", "passive"),
    ]


def test_condition_on_state_name_takes_snapshot(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, fire={"post_int": "passive", "pre_ext": "passive"})

    files = sorted(os.listdir(tmp_path / "snapshot"))
    assert files == ["[ext_before]B.simx", "[int_after]B.simx"]
    with open(tmp_path / "snapshot" / "[int_after]B.simx", "rb") as f:
        info = dill.load(f)
    assert info["name"] == "B"
    assert info["data"]._cur_state == "passive"


def test_confluent_pre_int_snapshot_holds_pre_transition_state(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, fire={"pre_int": "active"})

    # Both pre_int calls see "active"; the later one overwrites the file,
    # and both are taken before the transition, in state "active".
    with open(tmp_path / "snapshot" / "[int_before]B.simx", "rb") as f:
        info = dill.load(f)
    assert info["data"]._cur_state == "active"


def test_executor_cur_state_follows_model(tmp_path, monkeypatch):
    _, _, se = _run(tmp_path, monkeypatch)

    executor = se.product_port_map[se.get_model("B")]
    assert executor.get_cur_state() == "passive"
    executor.init_state("active")
    assert se.get_model("B")._cur_state == "active"
    assert executor.get_behavior_executor().get_cur_state() == "active"
