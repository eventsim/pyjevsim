"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Regression test: two executors that share an obj_id (one model snapshot
restored twice) must not stall V_TIME advancement when one is removed.
register_entity now refuses the second model, so the test builds that
state past the check.
"""
import copy
import threading

import pytest

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor


class _Once(BehaviorModel):
    def __init__(self, name):
        super().__init__(name)
        self.insert_state("wait", 5)
        self.insert_state("idle", Infinite)
        self.init_state("wait")
        self.insert_output_port("out")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self._cur_state = "idle"

    def output(self, msg_deliver):
        return None


def test_removed_duplicate_obj_id_does_not_stall_time():
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    proto = _Once("p")
    a = copy.deepcopy(proto)
    a.set_name("a")
    b = copy.deepcopy(proto)
    b.set_name("b")
    assert a.get_obj_id() == b.get_obj_id()
    ss.register_entity(a)
    with pytest.raises(ValueError, match="object ID"):
        ss.register_entity(b, dest_t=1)
    ss._waiting_ids.clear()
    ss.register_entity(b, dest_t=1)
    ss.create_entity()
    ss.remove_entity("dc")

    worker = threading.Thread(target=ss.simulate, args=(20, False), daemon=True)
    worker.start()
    worker.join(10)
    assert not worker.is_alive(), "simulate() stopped advancing time"
    assert ss.global_time == 20
