"""DEVStone atomic for pyjevsim.

Matches the semantics of `xdevs.examples.devstone.DelayedAtomic`:

  - passive on initialise.
  - On external input, optionally burn `ext_cycles` of synthetic CPU work and
    activate (deadline 0 -> fire immediately on next tick).
  - On internal transition, optionally burn `int_cycles`, emit a single
    output, and return to passive.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.system_message import SysMessage


def _burn(cycles: int) -> int:
    if cycles <= 0:
        return 0
    acc = 0
    for i in range(cycles):
        acc = (acc + i) ^ (i << 1)
    return acc


class DEVStoneAtomic(BehaviorModel):
    def __init__(self, name: str, int_cycles: int = 0, ext_cycles: int = 0):
        super().__init__(name)

        self.insert_state("passive")
        self.insert_state("active", 0)
        self.init_state("passive")

        self.insert_input_port("in")
        self.insert_output_port("out")

        self._int_cycles = int_cycles
        self._ext_cycles = ext_cycles
        self._n_externals = 0
        self._n_internals = 0
        self._n_events = 0

    def ext_trans(self, port, msg):
        if port != "in":
            return
        _burn(self._ext_cycles)
        self._n_externals += 1
        self._n_events += len(msg.retrieve())
        self._cur_state = "active"

    def int_trans(self):
        if self._cur_state == "active":
            _burn(self._int_cycles)
            self._n_internals += 1
            self._cur_state = "passive"

    def output(self, msg_deliver):
        sys_msg = SysMessage(self.get_name(), "out")
        sys_msg.insert(0)
        msg_deliver.insert_message(sys_msg)


class Seeder(BehaviorModel):
    """Seed generator: fires at t=0, then every `period` until `events` sent.

    With the default events=1 it is the original one-shot seeder (fires a
    single event at t=0 then passivates); the "wait" state is only added in
    multi-event mode. The seeder is not part of the counted atomics, so its
    own transitions never enter the transition totals.
    """

    def __init__(self, name: str = "seeder", events: int = 1,
                 period: float = 1.0):
        super().__init__(name)
        self.insert_state("active", 0)
        self.insert_state("done")
        if events > 1:
            self.insert_state("wait", period)
        self.init_state("active")
        self.insert_output_port("out")
        self._remaining = events

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state in ("active", "wait"):
            self._remaining -= 1
            self._cur_state = "wait" if self._remaining > 0 else "done"

    def output(self, msg_deliver):
        if self._cur_state in ("active", "wait"):
            sys_msg = SysMessage(self.get_name(), "out")
            sys_msg.insert(0)
            msg_deliver.insert_message(sys_msg)
