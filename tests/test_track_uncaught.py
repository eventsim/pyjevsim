"""Tests for the ``track_uncaught`` opt-in flag on ``SysExecutor``.

Default (``track_uncaught=False``): output messages emitted to ports
with no downstream coupling are dropped silently — the simulator's
``DefaultMessageCatcher`` (``self.dmc``) receives nothing.

Debug (``track_uncaught=True``): the dmc model receives every uncoupled
emit on its ``"uncaught"`` input port, which lets a user attach probes
or inspect what the model graph is leaking.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class _Emitter(BehaviorModel):
    """Fires once at t=0, emitting an integer on a port that nobody
    listens on (no coupling installed for it)."""

    def __init__(self):
        super().__init__("emitter")
        self.insert_state("active", 0)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("dangling")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "dangling")
            m.insert(42)
            msg_deliver.insert_message(m)


def _patch_dmc_to_count(ss):
    """Wrap ``ss.dmc.ext_trans`` so we can assert it was / wasn't called."""
    received = []
    original = ss.dmc.ext_trans

    def counting_ext_trans(port, msg):
        received.append((port, msg))
        return original(port, msg)

    ss.dmc.ext_trans = counting_ext_trans
    return received


def test_default_drops_uncoupled_emits():
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    received = _patch_dmc_to_count(ss)
    ss.register_entity(_Emitter())

    ss.simulate(2, _tm=False)

    assert received == [], (
        f"dmc should not receive uncoupled emits by default, got {received}"
    )


def test_track_uncaught_routes_to_dmc():
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None,
                     track_uncaught=True)
    received = _patch_dmc_to_count(ss)
    ss.register_entity(_Emitter())

    ss.simulate(2, _tm=False)

    assert len(received) == 1, (
        f"expected exactly one uncaught emit at dmc, got {received}"
    )
    port, msg = received[0]
    assert port == "uncaught"
    assert msg.retrieve() == [42]
