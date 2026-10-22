"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Regression tests for SystemObject ID allocation.
"""
import dill

from pyjevsim.behavior_executor import BehaviorExecutor
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.schedule_queue import ScheduleQueue
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_object import SystemObject
from pyjevsim.system_message import SysMessage


def test_ids_are_unique_and_increasing():
    objs = [SystemObject() for _ in range(5000)]
    ids = [o.get_obj_id() for o in objs]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    assert SysMessage("src", "dst").get_obj_id() > ids[-1]
    assert objs[0] < objs[1]


class _Relay(BehaviorModel):
    """Passive until an input arrives, then emits once after one tick."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("idle", Infinite)
        self.insert_state("busy", 1)
        self.init_state("idle")
        self.insert_input_port("in")
        self.insert_output_port("out")

    def ext_trans(self, port, msg):
        self._cur_state = "busy"

    def int_trans(self):
        self._cur_state = "idle"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "out")
        msg.insert(1)
        msg_deliver.insert_message(msg)


_HOT_PATH_CLASSES = (SystemObject, SysMessage, BehaviorModel,
                     BehaviorExecutor, ScheduleQueue)


def _class_attribute_ids():
    return {cls.__qualname__: {k: id(v) for k, v in vars(cls).items()}
            for cls in _HOT_PATH_CLASSES}


def _exercise_hot_path(n_objects):
    for _ in range(n_objects):
        SysMessage("src", "dst")
    models = [_Relay(f"relay{i}") for i in range(n_objects)]
    # Executors and the schedule queue: register a chain, kick its head and
    # run it, so BehaviorExecutor and ScheduleQueue methods all execute.
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    se.insert_input_port("start")
    chain = models[:200]
    for model in chain:
        se.register_entity(model)
    se.coupling_relation(se, "start", chain[0], "in")
    for a, b in zip(chain, chain[1:]):
        se.coupling_relation(a, "out", b, "in")
    se.insert_external_event("start", None)
    se.simulate(len(chain) + 5, _tm=False)


def test_instantiation_does_not_rebind_class_attributes():
    # Rebinding a class attribute per instance invalidates the type version
    # of the class and all its subclasses, which disables CPython's
    # attribute specialisation once the per-type cap is exhausted (#41).
    # Guard every class on the per-transition path: creating 5000 messages
    # and models, building executors and running the schedule queue must
    # leave every class attribute bound to the same object.
    _exercise_hot_path(10)  # one-time lazy set-up, if any, happens here
    before = _class_attribute_ids()
    _exercise_hot_path(5000)
    after = _class_attribute_ids()
    for name in before:
        assert before[name] == after[name], (
            f"{name} class attributes were rebound: "
            f"{sorted(k for k in before[name] if before[name][k] != after[name].get(k))}"
            f" added {sorted(set(after[name]) - set(before[name]))}")


def test_sys_message_shares_the_id_stream():
    a = SystemObject()
    m = SysMessage("src", "dst")
    b = SystemObject()
    assert a.get_obj_id() < m.get_obj_id() < b.get_obj_id()
    assert a < m < b


def test_sys_message_state_and_pickle_round_trip():
    m = SysMessage("src", "dst")
    assert m.get_msg_time() == -1
    m.insert([1, 2])
    copy = dill.loads(dill.dumps(m))
    assert copy.get_obj_id() == m.get_obj_id()
    assert (copy.get_src(), copy.get_dst(), copy.retrieve()) == ("src", "dst", [[1, 2]])
    assert copy.get_msg_time() == -1
    m.set_msg_time(3.5)
    assert m.get_msg_time() == 3.5
    assert SysMessage().get_msg_time() == -1


def test_sys_message_instance_state_matches_system_object_layout():
    # Pickles must stay loadable by releases that build SysMessage through
    # SystemObject.__init__, so the instance dict keeps the same keys.
    m = SysMessage("src", "dst")
    assert list(vars(m)) == [
        "_SystemObject__object_id", "_src", "_dst", "_msg_time", "_msg_list"]
