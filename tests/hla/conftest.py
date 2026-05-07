"""Shared fixtures for the HLA subsystem test suite.

These fixtures are deliberately minimal — they exist so the milestone
test files can stay focused on their own acceptance criteria. Anything
broader (multi-federate harness, gateway double, etc.) belongs in the
test file that needs it, not here.
"""

from __future__ import annotations

import pytest

from pyjevsim import BehaviorModel, SysMessage


# --------------------------------------------------------------------- models


class EmitOnce(BehaviorModel):
    """Fires a single SysMessage at t=0 on the named output port.

    Used to drive a single deterministic round of the schedule loop in
    HLAExecutor / factory tests where the test only cares that *some*
    output flowed.
    """

    def __init__(self, name: str = "emitter", out_port: str = "out", payload=None):
        super().__init__(name)
        self.insert_state("active", 0)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port(out_port)
        self._out_port = out_port
        self._payload = {"hello": "world"} if payload is None else payload

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._cur_state = "done"

    def output(self, deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), self._out_port)
            m.insert(self._payload)
            deliver.insert_message(m)


class RecordingReceiver(BehaviorModel):
    """Records every (port, payload) pair delivered via ext_trans."""

    def __init__(self, name: str = "receiver", in_port: str = "in"):
        super().__init__(name)
        self.insert_state("idle")
        self.init_state("idle")
        self.insert_input_port(in_port)
        self._in_port = in_port
        self.received: list[tuple[str, object]] = []

    def ext_trans(self, port, msg):
        items = msg.retrieve() if msg is not None else []
        payload = items[0] if items else None
        self.received.append((port, payload))

    def int_trans(self):
        pass

    def output(self, deliver):
        pass


class ConfluentCounter(BehaviorModel):
    """Counts int / ext / con transitions then passivates.

    Single-fire by design: after any of int_trans / ext_trans / con_trans
    runs, state moves to "done" (Infinite deadline) so the model is no
    longer imminent. This avoids the deadline=0 + no-passivation infinite
    cascade in SysExecutor.step's round loop.
    """

    def __init__(self, name: str = "counter", deadline: float = 1.0):
        super().__init__(name)
        if deadline < 0:
            raise ValueError("deadline must be >= 0")
        self.insert_state("active", deadline)
        self.insert_state("done")           # passive (Infinite deadline)
        self.init_state("active")
        self.insert_input_port("in")
        self.insert_output_port("out")
        self.n_int = 0
        self.n_ext = 0
        self.n_con = 0

    def ext_trans(self, port, msg):
        self.n_ext += 1
        self._cur_state = "done"

    def int_trans(self):
        self.n_int += 1
        self._cur_state = "done"

    def con_trans(self, port_msgs):
        self.n_con += 1
        self._cur_state = "done"

    def output(self, deliver):
        m = SysMessage(self.get_name(), "out")
        m.insert({"tick": self.n_int})
        deliver.insert_message(m)


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def emitter():
    return EmitOnce(name="emitter")


@pytest.fixture
def receiver():
    return RecordingReceiver(name="receiver")


@pytest.fixture
def counter():
    return ConfluentCounter(name="counter")
