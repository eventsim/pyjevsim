"""Scenario models for the trace oracle.

These are copies of the models and builders the oracle scenarios were first
written against (``tests/model_stm.py``, ``tests/model_peg.py``,
``tests/model_msg_recv.py`` and the ``_build`` helpers of
``tests/test_cancel_rescheduling.py``, ``tests/test_v_time_jump.py`` and
``tests/test_entity_destruction.py`` at v2.2.0).  They live here so that
editing a unit test cannot change a golden hash: only the engine, the
examples and ``benchmark/devstone`` of the checkout under test do.

Changing anything in this file changes the hashes of the scenarios that use
it and needs a ledger entry (see ``LEDGER.md``).  Model names, attribute
names and printed text are part of the trace.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.structural_model import StructuralModel
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


# tests/model_peg.py, tests/model_msg_recv.py, tests/model_stm.py

class PEG(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)
        self.insert_input_port("start")
        self.insert_output_port("process")
        self.msg_no = 0

    def ext_trans(self, port, msg):
        if port == "start":
            print("[Gen][IN]: started")
            self._cur_state = "Generate"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"{self.msg_no}")
        print(f"[Gen][OUT]: {self.msg_no}")
        msg_deliver.insert_message(msg)

    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.msg_no += 1


class MsgRecv(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_input_port("recv")
        self.msg_recv = 0

    def ext_trans(self, port, msg):
        if port == "recv":
            self._cur_state = "Wait"
            data = msg.retrieve()
            print(f"[MsgRecv][IN]: {data[0]}")
            self.msg_recv += 1

    def output(self, msg_deliver):
        return None

    def int_trans(self):
        if self._cur_state == "Wait":
            self._cur_state = "Wait"


class STM(StructuralModel):
    def __init__(self, name):
        super().__init__(name)
        self.insert_input_port("start")
        self.insert_output_port("output")
        peg = PEG("GEN")
        proc = MsgRecv("Proc")
        self.register_entity(peg)
        self.register_entity(proc)
        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")


# tests/test_confluent.py

class OneShotEmitter(BehaviorModel):
    """Fires output once at t=0 then passivates."""

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


class CounterAtomic(BehaviorModel):
    """Counts every transition kind it sees."""

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
        self._cur_state = "passive"
        for _ in port_msgs:
            self._cur_state = "active"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(1)
            msg_deliver.insert_message(m)


# tests/test_cancel_rescheduling.py

class Ticker(BehaviorModel):
    """Fires every ``period``; optionally cancels rescheduling on a poke."""

    def __init__(self, period, use_cancel, log, ss_ref):
        super().__init__("ticker")
        self.insert_state("tick", period)
        self.init_state("tick")
        self.insert_input_port("poke")
        self._use_cancel = use_cancel
        self._log = log
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        if port == "poke" and self._use_cancel:
            self.cancel_rescheduling()

    def int_trans(self):
        self._log.append(self._ss.global_time)
        self._cur_state = "tick"

    def output(self, msg_deliver):
        pass


class Poker(BehaviorModel):
    """Emits ``count`` pokes spaced one tick apart, then passivates."""

    def __init__(self, count, ss_ref):
        super().__init__("poker")
        self.insert_state("active", 1)
        self.insert_state("done", Infinite)
        self.init_state("active")
        self.insert_output_port("out")
        self._count = count
        self._fired = 0
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._fired += 1
            if self._fired >= self._count:
                self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(self._fired)
            msg_deliver.insert_message(m)


def build_cancel(use_cancel, poke_count):
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ticker = Ticker(period=5, use_cancel=use_cancel, log=log, ss_ref=ss)
    poker = Poker(count=poke_count, ss_ref=ss)
    ss.register_entity(ticker)
    ss.register_entity(poker)
    ss.coupling_relation(poker, "out", ticker, "poke")
    return ss, log


# tests/test_v_time_jump.py

class PeriodicGen(BehaviorModel):
    """Fires ``count`` events spaced by ``period``; logs the engine time."""

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


def build_vtime(period, count):
    gen_log = []
    sink_log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = PeriodicGen(period, count, gen_log, ss)
    sink = CountingSink(sink_log, ss)
    ss.register_entity(gen)
    ss.register_entity(sink)
    ss.coupling_relation(gen, "out", sink, "in")
    return ss, gen_log, sink_log


# tests/test_entity_destruction.py

class IdleModel(BehaviorModel):
    """Never schedules an internal event; only destruction removes it."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("idle", Infinite)
        self.init_state("idle")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass


def build_destruction(destruction_times):
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    for i, dest_t in enumerate(destruction_times):
        ss.register_entity(IdleModel(f"m{i}"), inst_t=0, dest_t=dest_t,
                           ename=f"m{i}")
    return ss
